import sqlalchemy as db


class Storage:
    def __init__(self):
        self.engine = db.create_engine('postgresql+psycopg2://postgres:1234@localhost/splitwise')
        self.conn = self.engine.connect()
        self.metadata = db.MetaData()

        self.Group = db.Table('Group', self.metadata,
                    db.Column('Id', db.Integer(), primary_key=True),
                         db.Column('ChatId', db.String(15), nullable=False),
                         db.Column('GroupName', db.String(63), nullable=False, unique=True)
                         )

        self.GroupUser = db.Table('GroupUser', self.metadata,
                                  db.Column('Id', db.Integer(), primary_key=True),
                                  db.Column('GroupId', db.Integer(), db.ForeignKey('Group.Id')),
                                  db.Column('UserId', db.String(127)),
                                  db.UniqueConstraint('GroupId', 'UserId', name='uq_groupuser_GroupId_UserId')
        )

        self.BalanceUserToUser = db.Table('BalanceToUser', self.metadata,
                                          db.Column('Id', db.Integer(), primary_key=True),
                                          db.Column('GroupId', db.Integer(), db.ForeignKey('Group.Id')),
                                          db.Column('FirstUserName', db.String(127)),
                                          db.Column('SecondUserName', db.String(127)),
                                          db.Column('Balance', db.Float(), default=0.0)
                                          )

        self.metadata.create_all(self.engine)

    def insert_group(self, chat_id, group_name):
        query = db.Insert(self.Group).values(ChatId=chat_id, GroupName=group_name)
        result = self.conn.execute(query)
        self.conn.commit()

    def select_group_from_chat_id(self, chat_id):
        query = db.select(self.Group.columns.GroupName).where(self.Group.columns.ChatId == str(chat_id))
        output = self.conn.execute(query)
        result = []
        for row in output:
            result.append(row.GroupName)
        return result

    def select_groupid_by_chatid_groupname(self, chat_id, group_name):
        query = db.select(self.Group.columns.Id
                          ).where(self.Group.columns.ChatId == str(chat_id)
                                  ).where(self.Group.columns.GroupName == str(group_name))
        output = self.conn.execute(query)

        result_id = -1
        for row in output:
            result_id = row.Id
        return result_id

    def select_groupid_by_groupname(self, group_name):
        query = db.select(self.Group.columns.Id).where(self.Group.columns.GroupName == str(group_name))
        output = self.conn.execute(query)

        result_id = -1
        for row in output:
            result_id = row.Id
        return result_id

    def select_users_from_group(self, group_id):
        query = db.select(self.GroupUser.columns.UserId).where(self.GroupUser.columns.GroupId == str(group_id))
        output = self.conn.execute(query)
        result = []
        for row in output:
            result.append(row.UserId)
        return result

    def insert_user_in_group(self, chat_id, group_name, user_name):
        group_id = self.select_groupid_by_chatid_groupname(chat_id, group_name)

        query = db.Insert(self.GroupUser).values(GroupId=group_id, UserId=user_name)
        self.conn.execute(query)

        all_group_user = self.select_users_from_group(group_id)
        for user in all_group_user:
            if user_name == user:
                continue

            query = db.Insert(self.BalanceUserToUser).values(GroupId=group_id, FirstUserName=user_name, SecondUserName=user)
            self.conn.execute(query)
            query = db.Insert(self.BalanceUserToUser).values(GroupId=group_id, FirstUserName=user, SecondUserName=user_name)
            self.conn.execute(query)

        self.conn.commit()

    def get_balances_group(self, group_name):
        group_id = self.select_groupid_by_groupname(group_name)
        query = db.select(self.BalanceUserToUser.columns.FirstUserName,
                           self.BalanceUserToUser.columns.SecondUserName,
                           self.BalanceUserToUser.columns.Balance).where(self.BalanceUserToUser.columns.GroupId == str(group_id))
        output = self.conn.execute(query)
        return output.fetchall()

    def change_balance(self, group_name, first_name, second_name, value_to_change):
        group_id = self.select_groupid_by_groupname(group_name)
        query = db.select(self.BalanceUserToUser.columns.Balance
                          ).where(self.BalanceUserToUser.columns.GroupId == str(group_id)
                          ).where(self.BalanceUserToUser.columns.FirstUserName == first_name
                          ).where(self.BalanceUserToUser.columns.SecondUserName == second_name)
        output = self.conn.execute(query)

        balance = -1
        for row in output:
            balance = row.Balance

        query = db.Update(self.BalanceUserToUser).where(self.BalanceUserToUser.columns.GroupId == str(group_id)
                          ).where(self.BalanceUserToUser.columns.FirstUserName == first_name
                          ).where(self.BalanceUserToUser.columns.SecondUserName == second_name).values(Balance=float(balance) + float(value_to_change))
        self.conn.execute(query)

        query = db.select(self.BalanceUserToUser.columns.Balance
                          ).where(self.BalanceUserToUser.columns.GroupId == str(group_id)
                                  ).where(self.BalanceUserToUser.columns.FirstUserName == second_name
                                          ).where(self.BalanceUserToUser.columns.SecondUserName == first_name)
        output = self.conn.execute(query)

        balance = -1
        for row in output:
            balance = row.Balance

        query = db.Update(self.BalanceUserToUser).where(self.BalanceUserToUser.columns.GroupId == str(group_id)
                                                        ).where(
            self.BalanceUserToUser.columns.FirstUserName == second_name
            ).where(self.BalanceUserToUser.columns.SecondUserName == first_name).values(
            Balance=float(balance) - float(value_to_change))
        self.conn.execute(query)
        self.conn.commit()
