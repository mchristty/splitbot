import sqlalchemy as db
from sqlalchemy.pool import QueuePool
from cache_manager import cache_manager


class Storage:
    def __init__(self):
        # Настройка пула соединений для поддержки множественных пользователей
        self.engine = db.create_engine(
            'postgresql+psycopg2://postgres:1234@localhost/splitwise',
            poolclass=QueuePool,
            pool_size=20,  # Количество соединений в пуле
            max_overflow=30,  # Дополнительные соединения при необходимости
            pool_pre_ping=True,  # Проверка соединений перед использованием
            pool_recycle=3600,  # Переиспользование соединений каждый час
            echo=False  # Отключить SQL логи для производительности
        )
        self.metadata = db.MetaData()

        self.Group = db.Table('Group', self.metadata,
                    db.Column('Id', db.Integer(), primary_key=True),
                         db.Column('ChatId', db.String(15), nullable=False),
                         db.Column('GroupName', db.String(63), nullable=False, unique=True),
                         db.Column('Currency', db.String(3), nullable=False, default='RUB'),
                         db.Index('idx_group_chatid', 'ChatId'),  # Индекс для быстрого поиска по ChatId
                         db.Index('idx_group_name', 'GroupName')  # Индекс для быстрого поиска по названию
                         )

        self.GroupUser = db.Table('GroupUser', self.metadata,
                                  db.Column('Id', db.Integer(), primary_key=True),
                                  db.Column('GroupId', db.Integer(), db.ForeignKey('Group.Id')),
                                  db.Column('UserId', db.String(127)),
                                  db.UniqueConstraint('GroupId', 'UserId', name='uq_groupuser_GroupId_UserId'),
                                  db.Index('idx_groupuser_groupid', 'GroupId'),  # Индекс для быстрого поиска по GroupId
                                  db.Index('idx_groupuser_userid', 'UserId')  # Индекс для быстрого поиска по UserId
        )

        self.BalanceUserToUser = db.Table('BalanceToUser', self.metadata,
                                          db.Column('Id', db.Integer(), primary_key=True),
                                          db.Column('GroupId', db.Integer(), db.ForeignKey('Group.Id')),
                                          db.Column('FirstUserName', db.String(127)),
                                          db.Column('SecondUserName', db.String(127)),
                                          db.Column('Balance', db.Float(), default=0.0),
                                          db.Column('Currency', db.String(3), nullable=False, default='RUB'),
                                          db.Index('idx_balance_groupid', 'GroupId'),  # Индекс для быстрого поиска по GroupId
                                          db.Index('idx_balance_firstuser', 'FirstUserName'),  # Индекс для быстрого поиска по FirstUserName
                                          db.Index('idx_balance_seconduser', 'SecondUserName'),  # Индекс для быстрого поиска по SecondUserName
                                          db.Index('idx_balance_composite', 'GroupId', 'FirstUserName', 'SecondUserName')  # Составной индекс
                                          )

        self.metadata.create_all(self.engine)

    def insert_group(self, chat_id, group_name, currency='RUB'):
        query = db.Insert(self.Group).values(ChatId=chat_id, GroupName=group_name, Currency=currency)
        with self.engine.connect() as conn:
            result = conn.execute(query)
            conn.commit()
        
        # Инвалидируем кэш
        cache_manager.delete(f"groups_chat_{chat_id}")
        cache_manager.delete(f"group_id_{group_name}")

    def select_group_from_chat_id(self, chat_id):
        cache_key = f"groups_chat_{chat_id}"
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        query = db.select(self.Group.columns.GroupName).where(self.Group.columns.ChatId == str(chat_id))
        with self.engine.connect() as conn:
            output = conn.execute(query)
            result = []
            for row in output:
                result.append(row.GroupName)
            
            # Кэшируем результат
            cache_manager.set(cache_key, result)
            return result

    def select_groupid_by_chatid_groupname(self, chat_id, group_name):
        query = db.select(self.Group.columns.Id
                          ).where(self.Group.columns.ChatId == str(chat_id)
                                  ).where(self.Group.columns.GroupName == str(group_name))
        with self.engine.connect() as conn:
            output = conn.execute(query)
            result_id = -1
            for row in output:
                result_id = row.Id
            return result_id

    def select_groupid_by_groupname(self, group_name):
        cache_key = f"group_id_{group_name}"
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        query = db.select(self.Group.columns.Id).where(self.Group.columns.GroupName == str(group_name))
        with self.engine.connect() as conn:
            output = conn.execute(query)
            result_id = -1
            for row in output:
                result_id = row.Id
            
            # Кэшируем результат
            cache_manager.set(cache_key, result_id)
            return result_id

    def select_users_from_group(self, group_id):
        query = db.select(self.GroupUser.columns.UserId).where(self.GroupUser.columns.GroupId == group_id)
        with self.engine.connect() as conn:
            output = conn.execute(query)
            result = []
            for row in output:
                result.append(row.UserId)
            return result

    def insert_user_in_group(self, chat_id, group_name, user_name):
        group_id = self.select_groupid_by_chatid_groupname(chat_id, group_name)

        with self.engine.connect() as conn:
            query = db.Insert(self.GroupUser).values(GroupId=group_id, UserId=user_name)
            conn.execute(query)

            all_group_user = self.select_users_from_group(group_id)
            for user in all_group_user:
                if user_name == user:
                    continue

                query = db.Insert(self.BalanceUserToUser).values(GroupId=group_id, FirstUserName=user_name, SecondUserName=user)
                conn.execute(query)
                query = db.Insert(self.BalanceUserToUser).values(GroupId=group_id, FirstUserName=user, SecondUserName=user_name)
                conn.execute(query)

            conn.commit()

    def get_balances_group(self, group_name):
        cache_key = f"balances_{group_name}"
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        group_id = self.select_groupid_by_groupname(group_name)
        query = db.select(self.BalanceUserToUser.columns.FirstUserName,
                           self.BalanceUserToUser.columns.SecondUserName,
                           self.BalanceUserToUser.columns.Balance,
                           self.BalanceUserToUser.columns.Currency).where(self.BalanceUserToUser.columns.GroupId == group_id)
        with self.engine.connect() as conn:
            output = conn.execute(query)
            result = output.fetchall()
            
            # Кэшируем результат
            cache_manager.set(cache_key, result)
            return result

    def change_balance(self, group_name, first_name, second_name, value_to_change, currency='RUB'):
        group_id = self.select_groupid_by_groupname(group_name)
        
        with self.engine.connect() as conn:
            # Проверяем, есть ли уже запись с такой валютой
            query = db.select(self.BalanceUserToUser.columns.Balance, self.BalanceUserToUser.columns.Currency
                              ).where(self.BalanceUserToUser.columns.GroupId == group_id
                              ).where(self.BalanceUserToUser.columns.FirstUserName == first_name
                              ).where(self.BalanceUserToUser.columns.SecondUserName == second_name
                              ).where(self.BalanceUserToUser.columns.Currency == currency)
            output = conn.execute(query)

            balance = 0.0  # По умолчанию баланс равен 0
            for row in output:
                balance = row.Balance

            # Обновляем или создаем запись для данной валюты
            if balance == 0.0 and not any(output.fetchall()):
                # Создаем новую запись
                query = db.Insert(self.BalanceUserToUser).values(
                    GroupId=group_id,
                    FirstUserName=first_name,
                    SecondUserName=second_name,
                    Balance=float(value_to_change),
                    Currency=currency
                )
                conn.execute(query)
            else:
                # Обновляем существующую запись
                query = db.Update(self.BalanceUserToUser).where(
                    self.BalanceUserToUser.columns.GroupId == group_id
                ).where(
                    self.BalanceUserToUser.columns.FirstUserName == first_name
                ).where(
                    self.BalanceUserToUser.columns.SecondUserName == second_name
                ).where(
                    self.BalanceUserToUser.columns.Currency == currency
                ).values(Balance=float(balance) + float(value_to_change))
                conn.execute(query)

            # Второе направление: second_name -> first_name
            query = db.select(self.BalanceUserToUser.columns.Balance
                              ).where(self.BalanceUserToUser.columns.GroupId == group_id
                              ).where(self.BalanceUserToUser.columns.FirstUserName == second_name
                              ).where(self.BalanceUserToUser.columns.SecondUserName == first_name
                              ).where(self.BalanceUserToUser.columns.Currency == currency)
            output = conn.execute(query)

            balance = 0.0  # По умолчанию баланс равен 0
            for row in output:
                balance = row.Balance

            if balance == 0.0 and not any(output.fetchall()):
                # Создаем новую запись
                query = db.Insert(self.BalanceUserToUser).values(
                    GroupId=group_id,
                    FirstUserName=second_name,
                    SecondUserName=first_name,
                    Balance=-float(value_to_change),
                    Currency=currency
                )
                conn.execute(query)
            else:
                # Обновляем существующую запись
                query = db.Update(self.BalanceUserToUser).where(
                    self.BalanceUserToUser.columns.GroupId == group_id
                ).where(
                    self.BalanceUserToUser.columns.FirstUserName == second_name
                ).where(
                    self.BalanceUserToUser.columns.SecondUserName == first_name
                ).where(
                    self.BalanceUserToUser.columns.Currency == currency
                ).values(Balance=float(balance) - float(value_to_change))
                conn.execute(query)
            
            conn.commit()
            
        # Инвалидируем кэш после изменения балансов
        cache_manager.delete(f"group_id_{group_name}")
        cache_manager.delete(f"balances_{group_name}")

    def is_user_in_group(self, group_name, user_name):
        """Проверяет, есть ли пользователь в группе"""
        group_id = self.select_groupid_by_groupname(group_name)
        if group_id == -1:
            return False
        
        query = db.select(self.GroupUser.columns.UserId).where(
            self.GroupUser.columns.GroupId == group_id
        ).where(self.GroupUser.columns.UserId == user_name)
        
        with self.engine.connect() as conn:
            output = conn.execute(query)
            result = output.fetchone()
            return result is not None

    def remove_user_from_group(self, group_name, user_name):
        """Удаляет пользователя из группы, перенося его траты под ником 'All'"""
        group_id = self.select_groupid_by_groupname(group_name)
        if group_id == -1:
            return False
        
        with self.engine.connect() as conn:
            # Сначала получаем все балансы, связанные с этим пользователем
            select_balances_query = db.select(
                self.BalanceUserToUser.columns.FirstUserName,
                self.BalanceUserToUser.columns.SecondUserName,
                self.BalanceUserToUser.columns.Balance
            ).where(
                self.BalanceUserToUser.columns.GroupId == group_id
            ).where(
                (self.BalanceUserToUser.columns.FirstUserName == user_name) |
                (self.BalanceUserToUser.columns.SecondUserName == user_name)
            )
            
            balances_to_transfer = conn.execute(select_balances_query).fetchall()
            
            # Переносим балансы под ником "All"
            for balance in balances_to_transfer:
                first_user = balance.FirstUserName
                second_user = balance.SecondUserName
                amount = balance.Balance
                
                # Определяем, кто должен кому
                if first_user == user_name:
                    # user_name должен second_user
                    # Переносим на "All" должен second_user
                    self._transfer_balance_to_all(conn, group_id, "All", second_user, amount)
                else:
                    # second_user должен user_name
                    # Переносим на second_user должен "All"
                    self._transfer_balance_to_all(conn, group_id, second_user, "All", amount)
            
            # Удаляем старые балансы
            delete_balances_query = db.delete(self.BalanceUserToUser).where(
                self.BalanceUserToUser.columns.GroupId == group_id
            ).where(
                (self.BalanceUserToUser.columns.FirstUserName == user_name) |
                (self.BalanceUserToUser.columns.SecondUserName == user_name)
            )
            
            conn.execute(delete_balances_query)
            
            # Удаляем пользователя из GroupUser
            delete_user_query = db.delete(self.GroupUser).where(
                self.GroupUser.columns.GroupId == group_id
            ).where(self.GroupUser.columns.UserId == user_name)
            
            result = conn.execute(delete_user_query)
            conn.commit()
            
            # Инвалидируем кэш после удаления пользователя
            cache_manager.delete(f"group_id_{group_name}")
            cache_manager.delete(f"balances_{group_name}")
            
            return result.rowcount > 0
    
    def _transfer_balance_to_all(self, conn, group_id, first_user, second_user, amount):
        """Переносит баланс под ником 'All'"""
        # Проверяем, существует ли уже баланс между этими пользователями
        existing_balance_query = db.select(self.BalanceUserToUser.columns.Balance).where(
            self.BalanceUserToUser.columns.GroupId == group_id
        ).where(
            self.BalanceUserToUser.columns.FirstUserName == first_user
        ).where(
            self.BalanceUserToUser.columns.SecondUserName == second_user
        )
        
        existing_balance = conn.execute(existing_balance_query).fetchone()
        
        if existing_balance:
            # Обновляем существующий баланс
            update_query = db.update(self.BalanceUserToUser).where(
                self.BalanceUserToUser.columns.GroupId == group_id
            ).where(
                self.BalanceUserToUser.columns.FirstUserName == first_user
            ).where(
                self.BalanceUserToUser.columns.SecondUserName == second_user
            ).values(Balance=existing_balance.Balance + amount)
            
            conn.execute(update_query)
        else:
            # Создаем новый баланс
            insert_query = db.insert(self.BalanceUserToUser).values(
                GroupId=group_id,
                FirstUserName=first_user,
                SecondUserName=second_user,
                Balance=amount
            )
            
            conn.execute(insert_query)
        
        # Обновляем обратный баланс
        reverse_existing_balance_query = db.select(self.BalanceUserToUser.columns.Balance).where(
            self.BalanceUserToUser.columns.GroupId == group_id
        ).where(
            self.BalanceUserToUser.columns.FirstUserName == second_user
        ).where(
            self.BalanceUserToUser.columns.SecondUserName == first_user
        )
        
        reverse_existing_balance = conn.execute(reverse_existing_balance_query).fetchone()
        
        if reverse_existing_balance:
            # Обновляем существующий обратный баланс
            reverse_update_query = db.update(self.BalanceUserToUser).where(
                self.BalanceUserToUser.columns.GroupId == group_id
            ).where(
                self.BalanceUserToUser.columns.FirstUserName == second_user
            ).where(
                self.BalanceUserToUser.columns.SecondUserName == first_user
            ).values(Balance=reverse_existing_balance.Balance - amount)
            
            conn.execute(reverse_update_query)
        else:
            # Создаем новый обратный баланс
            reverse_insert_query = db.insert(self.BalanceUserToUser).values(
                GroupId=group_id,
                FirstUserName=second_user,
                SecondUserName=first_user,
                Balance=-amount
            )
            
            conn.execute(reverse_insert_query)

    def delete_group(self, group_id):
        """Удаляет группу и все связанные с ней данные"""
        try:
            # Валидация входных параметров
            if group_id is None:
                return False
            
            if not isinstance(group_id, int):
                return False
            
            if group_id <= 0:
                return False
            
            # Получаем информацию о группе для очистки кэша
            group_info_query = db.select(self.Group.columns.ChatId, self.Group.columns.GroupName).where(
                self.Group.columns.Id == group_id
            )
            
            with self.engine.connect() as conn:
                group_info_result = conn.execute(group_info_query)
                group_info = group_info_result.fetchone()
                
                if not group_info:
                    return False
                
                chat_id = group_info.ChatId
                group_name = group_info.GroupName
                # Удаляем все балансы группы
                delete_balances_query = db.delete(self.BalanceUserToUser).where(
                    self.BalanceUserToUser.columns.GroupId == group_id
                )
                balances_result = conn.execute(delete_balances_query)
                
                # Удаляем всех пользователей группы
                delete_users_query = db.delete(self.GroupUser).where(
                    self.GroupUser.columns.GroupId == group_id
                )
                users_result = conn.execute(delete_users_query)
                
                # Удаляем саму группу
                delete_group_query = db.delete(self.Group).where(
                    self.Group.columns.Id == group_id
                )
                group_result = conn.execute(delete_group_query)
                
                conn.commit()
                
                # Очищаем кэш после успешного удаления
                cache_manager.delete(f"groups_chat_{chat_id}")
                cache_manager.delete(f"group_id_{group_name}")
                
                return group_result.rowcount > 0
        except Exception as e:
            return False

    def get_group_currency(self, group_name):
        """Получает валюту группы"""
        group_id = self.select_groupid_by_groupname(group_name)
        if group_id == -1:
            return 'RUB'  # Возвращаем валюту по умолчанию
        
        with self.engine.connect() as conn:
            query = db.select(self.Group.columns.Currency).where(self.Group.columns.Id == group_id)
            result = conn.execute(query)
            
            for row in result:
                return row.Currency or 'RUB'
            
            return 'RUB'  # Возвращаем валюту по умолчанию
