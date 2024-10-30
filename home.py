from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os
from datetime import datetime, timedelta, timezone
from flask_sqlalchemy import SQLAlchemy
import pytz
import csv

app = Flask(__name__)  # 创建 Flask 应用

users = {
    'cuhksz': '123456'
}


app.secret_key = os.urandom(24)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///games.db'

beijing_tz = pytz.timezone('Asia/Shanghai')

db = SQLAlchemy(app)

class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

    east_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    south_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    west_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    north_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    
    east_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)
    south_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)
    west_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)
    north_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)
    db.Column(db.Date, nullable=True)

    east_player = db.relationship('Member', foreign_keys=[east_player_id])
    south_player = db.relationship('Member', foreign_keys=[south_player_id])
    west_player = db.relationship('Member', foreign_keys=[west_player_id])
    north_player = db.relationship('Member', foreign_keys=[north_player_id])

    east_team = db.relationship('Team', foreign_keys=[east_team_id])
    south_team = db.relationship('Team', foreign_keys=[south_team_id])
    west_team = db.relationship('Team', foreign_keys=[west_team_id])
    north_team = db.relationship('Team', foreign_keys=[north_team_id])

class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

class Round(db.Model):
    __tablename__ = 'rounds'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id', ondelete='CASCADE'), nullable=False)
    east_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    south_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    west_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    north_player_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    east_score = db.Column(db.Integer, nullable=False)
    south_score = db.Column(db.Integer, nullable=False)
    west_score = db.Column(db.Integer, nullable=False)
    north_score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(beijing_tz).replace(microsecond=0))

    # Define relationships
    game = db.relationship('Game', backref=db.backref('rounds', lazy=True))
    east_player = db.relationship('Member', foreign_keys=[east_player_id])
    south_player = db.relationship('Member', foreign_keys=[south_player_id])
    west_player = db.relationship('Member', foreign_keys=[west_player_id])
    north_player = db.relationship('Member', foreign_keys=[north_player_id])

    def __init__(self, game_id, east_player_id, south_player_id, west_player_id, north_player_id, east_score, south_score, west_score, north_score):
        self.game_id = game_id
        self.east_player_id = east_player_id
        self.south_player_id = south_player_id
        self.west_player_id = west_player_id
        self.north_player_id = north_player_id
        self.east_score = east_score
        self.south_score = south_score
        self.west_score = west_score
        self.north_score = north_score


class Member(db.Model):
    __tablename__ = 'members'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)

    point_punishment = db.Column(db.Integer, nullable=True)

# 定义比赛模型
class Game(db.Model):
    __tablename__ = 'game'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rules = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('admin', tab='home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 验证用户名和密码
        if username in users and users[username] == password:
            session['logged_in'] = True  # 设置登录状态
            session['last_active'] = datetime.now().timestamp()  # save lastlogin time
            session.parmanent = True
            return redirect(url_for('admin'))  # 登录成功后重定向到主页
        else:
            flash('用户名或密码错误，请重试。', 'error')

    return render_template('login.html')  # GET 请求时返回登录页面

# 检查是否已登录
def is_logged_in():
    if session.get('logged_in'):
        # 检查会话时限
        last_active = session.get('last_active')
        if last_active:
            current_time = datetime.now().timestamp()
            # 如果最后活跃时间超过30分钟，认为会话已超时
            if current_time - last_active > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                session.clear()  # 清除 session 数据
                return False
            else:
                session['last_active'] = current_time  # 更新最后活跃时间
                return True
    return False

@app.route('/admin')
def admin():
    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面

    tab = request.args.get('tab', 'home')  # 获取 tab 参数，默认为 'home'

    if request.method == 'POST' and tab == 'add_game':
        return add_game()  # 调用 add_game 函数
    
    games = Game.query.all() if tab == 'manage_game' else None 

    return render_template('admin.html', tab=tab, games=games)

@app.route('/add_game', methods=['POST'])
def add_game():
    game_name = request.form.get('game_name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    game_rules = request.form.get('game_rules')

    # 判断截止日期是否小于开始日期
    if datetime.strptime(end_date, '%Y-%m-%d') < datetime.strptime(start_date, '%Y-%m-%d'):
        flash('截止日期不能小于开始日期！', 'error')  # 显示错误信息
        return redirect(url_for('admin', tab='add_game'))  # 重定向回管理页面
    
    new_game = Game(
        name=game_name,
        start_date=datetime.strptime(start_date, '%Y-%m-%d'),
        end_date=datetime.strptime(end_date, '%Y-%m-%d'),
        rules=game_rules
    )

    # 将比赛保存到数据库
    db.session.add(new_game)
    db.session.commit()
    
    flash('比赛信息添加成功！', 'success')  # 显示成功消息
    return redirect(url_for('admin', tab='home'))   # 返回到管理页面

@app.route('/')  # 定义首页（根路径）的 URL 路由
def home():
    games = Game.query.all()
    return render_template('index.html', games=games)  # 访问首页时显示的文字

@app.route('/logout')
def logout():
    session.clear()  # 清除 session 数据
    flash('您已成功登出。', 'success')
    return redirect(url_for('login'))  # 重定向到登录页面

@app.route('/delete_game', methods=['POST'])
def delete_game():
    game_id = request.form.get('game_id')

    members = Member.query.filter_by(game_id=game_id).all()
    for member in members:
        db.session.delete(member)
    
    # 查询比赛并删除
    game = Game.query.get(game_id)
    if game:
        db.session.delete(game)
        db.session.commit()
        flash('比赛删除成功！', 'success')
    else:
        flash('未找到该比赛！', 'error')
    return redirect(url_for('admin', tab='manage_game'))  # 重定向回比赛管理页面

@app.route('/manage_game/<int:game_id>', methods=['GET', 'POST'])
def manage_game(game_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'home')  # 获取 tab 参数，默认为 'home'
    game = Game.query.get(game_id)
    members = Member.query.filter_by(game_id=game_id).all()
    rounds = Round.query.filter_by(game_id=game_id).all()
    teams = Team.query.filter_by(game_id=game_id).all()
    return render_template('manage.html', tab=tab, game=game, members=members, rounds=rounds, teams=teams)

@app.route('/update_game/<int:game_id>', methods=['POST'])
def update_game(game_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    # 查询要修改的比赛
    game = Game.query.get(game_id)

    tab = request.args.get('tab', 'home')
    
    if game:
        # 获取表单提交的数据
        game_name = request.form.get('game_name')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        game_rules = request.form.get('game_rules')

        # 将字符串日期转换为 date 对象
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 判断截止日期不能小于开始日期
        if end_date < start_date:
            flash('截止日期不能小于开始日期！', 'error')
            return redirect(url_for('manage_game', game_id=game_id))

        # 更新比赛信息
        game.name = game_name
        game.start_date = start_date
        game.end_date = end_date
        game.rules = game_rules

        # 提交修改到数据库
        db.session.commit()

        flash('比赛信息修改成功！', 'success')
        return redirect(url_for('manage_game', game_id=game_id, tab=tab))
    else:
        flash('未找到该比赛！', 'error')
        return redirect(url_for('manage_game'))
    
@app.route('/add_member/<int:game_id>', methods=['POST'])
def add_member(game_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'member_management')
    game = Game.query.get(game_id)

    member_name = request.form.get('member_name')
    if game.rules == 'M-League团体赛':
        team_id = request.form.get('member_team')
        new_member = Member(name=member_name, game_id=game_id, team_id=team_id, point_punishment=0)
    else:
        new_member = Member(name=member_name, game_id=game_id, point_punishment=0)
    
    db.session.add(new_member)
    db.session.commit()
    
    return redirect(url_for('manage_game', game_id=game_id, tab=tab))

@app.route('/edit_member/<int:member_id>', methods=['POST'])
def edit_member(member_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'member_management')
    

    member = Member.query.get(member_id)

    game = Game.query.get(member.game_id)

    if member:
        member_name = request.form.get('member_name')
        if game.rules == 'M-League团体赛':
            team_id = request.form.get('member_team')
            member.team_id = team_id
        member.name = member_name
        # 提交修改到数据库
        db.session.commit()

        flash('成员信息修改成功！', 'success')
        return redirect(url_for('manage_game', game_id=member.game_id, tab=tab))
    else:
        flash('未找到该成员！', 'error')
        return redirect(url_for('manage_game'))
    
@app.route('/punishment/<int:member_id>', methods=['POST'])
def punishment(member_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'member_management')
    

    member = Member.query.get(member_id)


    if member:
        punishpt = request.form.get('punishpt')
        member.point_punishment = punishpt
        # 提交修改到数据库
        db.session.commit()

        flash('罚点修改成功！', 'success')
        return redirect(url_for('manage_game', game_id=member.game_id, tab=tab))
    else:
        flash('未找到该成员！', 'error')
        return redirect(url_for('manage_game'))
    

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'member_management')

    member = Member.query.get(member_id)
    if member:
        db.session.delete(member)
        db.session.commit()
        flash('成员信息删除成功！', 'success')
    else:
        flash('成员信息删除失败！', 'error')
    
    return redirect(url_for('manage_game', game_id=member.game_id, tab=tab))

@app.route('/add_round/<int:game_id>', methods=['GET', 'POST'])
def add_round(game_id):
    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'result_input')
    members = Member.query.filter_by(game_id=game_id).all()

    if request.method == 'POST':
        # 获取表单中的数据
        east_player_id = request.form.get('east_player_id')
        south_player_id = request.form.get('south_player_id')
        west_player_id = request.form.get('west_player_id')
        north_player_id = request.form.get('north_player_id')
        east_score = int(request.form.get('east_score'))
        south_score = int(request.form.get('south_score'))
        north_score = int(request.form.get('north_score'))
        west_score = int(request.form.get('west_score'))

        if east_score + south_score + north_score + west_score != 100000:
            flash('总点数不为100000点！请重新输入！', 'error')
            return redirect(url_for('manage_game', game_id=game_id, tab=tab))
        
        # 将四个选手ID放入一个列表
        player_ids = [east_player_id, south_player_id, west_player_id, north_player_id]

        # 使用 set 来检查是否有重复的ID
        if len(player_ids) != len(set(player_ids)):
            # 如果有重复的ID，显示错误消息并返回
            flash('选手不能重复，请重新选择！', 'error')
            return redirect(url_for('manage_game', game_id=game_id, tab=tab))

        # 创建新的对局记录
        new_round = Round(
            game_id=game_id,
            east_player_id=east_player_id,
            south_player_id=south_player_id,
            west_player_id=west_player_id,
            north_player_id=north_player_id,
            east_score=east_score,
            south_score=south_score,
            west_score=west_score,
            north_score=north_score
        )
        
        db.session.add(new_round)
        db.session.commit()
        
        flash('对局信息已添加', 'success')
        return redirect(url_for('manage_game', game_id=game_id, tab=tab))
    
@app.route('/delete_round/<int:round_id>', methods=['POST'])
def delete_round(round_id):
    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))
    
    tab = request.args.get('tab', 'result_input')

    # 查询要删除的对局
    round_to_delete = Round.query.get_or_404(round_id)

    try:
        db.session.delete(round_to_delete)
        db.session.commit()
        flash('对局已成功删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除对局时出错: {e}', 'error')

    return redirect(url_for('manage_game', game_id=round_to_delete.game_id, tab=tab))

@app.route('/edit_round/<int:round_id>', methods=['GET', 'POST'])
def edit_round(round_id):
    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'result_input')
    round = Round.query.get(round_id)
    members = Member.query.filter_by(game_id=round.game_id).all()

    if request.method == 'POST':
        # 获取表单中的数据
        east_player_id = request.form.get('east_player_id')
        south_player_id = request.form.get('south_player_id')
        west_player_id = request.form.get('west_player_id')
        north_player_id = request.form.get('north_player_id')
        east_score = int(request.form.get('east_score'))
        south_score = int(request.form.get('south_score'))
        north_score = int(request.form.get('north_score'))
        west_score = int(request.form.get('west_score'))

        if east_score + south_score + north_score + west_score != 100000:
            flash('总点数不为100000点！请重新输入！', 'error')
            return redirect(url_for('manage_game', game_id=round.game_id, tab=tab))
        
        # 将四个选手ID放入一个列表
        player_ids = [east_player_id, south_player_id, west_player_id, north_player_id]

        # 使用 set 来检查是否有重复的ID
        if len(player_ids) != len(set(player_ids)):
            # 如果有重复的ID，显示错误消息并返回
            flash('选手不能重复，请重新选择！', 'error')
            return redirect(url_for('manage_game', game_id=round.game_id, tab=tab))

        round.east_player_id = east_player_id
        round.south_player_id = south_player_id
        round.west_player_id = west_player_id
        round.north_player_id = north_player_id
        round.east_score = east_score
        round.south_score = south_score
        round.west_score = west_score
        round.north_score = north_score
        
        db.session.commit()
        flash('对局信息编辑成功！', 'success')
        return redirect(url_for('manage_game', game_id=round.game_id, tab=tab))

def team_ranking_table(game):
    
    teams = Team.query.filter_by(game_id=game.id).all()
    rounds = Round.query.filter_by(game_id=game.id).all()
    team_data = []

    for team in teams:
        total_score = 0.0
        total_original_point = 0.0
        total_games = 0
        first_place = 0
        second_place = 0
        third_place = 0
        fourth_place = 0
        punishment = 0

        members = Member.query.filter_by(team_id=team.id).all()

        for _member in members:
            punishment += _member.point_punishment

        for _round in rounds:
            score = [int(_round.east_score), int(_round.west_score), int(_round.south_score), int(_round.north_score)]
            playerscore = int(123123123)
            if _round.east_player.team_id == team.id:
                playerscore = int(_round.east_score)
            elif _round.west_player.team_id == team.id:
                playerscore = int(_round.west_score)
            elif _round.south_player.team_id == team.id:
                playerscore = int(_round.south_score)
            elif _round.north_player.team_id == team.id:
                playerscore = int(_round.north_score)
            if playerscore != 123123123:
                total_games = total_games + 1
                count = sum(1 for x in score if x < playerscore)
                count = 4 - count
                if count == 1:
                    first_place = first_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 + 50.0
                        total_score = round(total_score, 1)
                elif count == 2:
                    second_place = second_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 + 10.0
                        total_score = round(total_score, 1)
                elif count == 3:
                    third_place = third_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 - 10.0
                        total_score = round(total_score, 1)
                elif count == 4:
                    fourth_place = fourth_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 - 30.0
                        total_score = round(total_score, 1)
                if game.rules == 'M-League团体赛':
                    total_original_point += float(playerscore - 25000) / 1000.0
                total_original_point = round(total_original_point, 1)

        total_score -= punishment

        total_score = round(total_score, 1)
        
        team_data.append({
            'id': team.id,
            'name': team.name,
            'total_score': total_score,
            'total_original_point': total_original_point,
            'total_games': total_games,
            'first_place': first_place,
            'second_place': second_place,
            'third_place': third_place,
            'fourth_place': fourth_place,
            'punishment': punishment
        })

    return sorted(team_data, key=lambda x: (x['total_games'] != 0, x['total_score']), reverse=True)

def member_ranking_table(game):
    members = Member.query.filter_by(game_id=game.id).all()
    rounds = Round.query.filter_by(game_id=game.id).all()
    member_data = []

    for member in members:
        total_score = 0.0
        total_original_point = 0.0
        total_games = 0
        average_rank = 0.0
        highest_point = 0
        first_place = 0
        second_place = 0
        third_place = 0
        fourth_place = 0
        punishment = member.point_punishment

        for _round in rounds:
            score = [int(_round.east_score), int(_round.west_score), int(_round.south_score), int(_round.north_score)]
            playerscore = int(123123123)
            if _round.east_player.id == member.id:
                playerscore = int(_round.east_score)
            elif _round.west_player.id == member.id:
                playerscore = int(_round.west_score)
            elif _round.south_player.id == member.id:
                playerscore = int(_round.south_score)
            elif _round.north_player.id == member.id:
                playerscore = int(_round.north_score)
            if playerscore != 123123123:
                total_games = total_games + 1
                count = sum(1 for x in score if x < playerscore)
                count = 4 - count
                if count == 1:
                    first_place = first_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 + 50.0
                        total_score = round(total_score, 1)
                elif count == 2:
                    second_place = second_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 + 10.0
                        total_score = round(total_score, 1)
                elif count == 3:
                    third_place = third_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 - 10.0
                        total_score = round(total_score, 1)
                elif count == 4:
                    fourth_place = fourth_place + 1
                    if game.rules == 'M-League团体赛':
                        total_score += float(playerscore - 30000) / 1000.0 - 30.0
                        total_score = round(total_score, 1)
                if game.rules == 'M-League团体赛':
                    total_original_point += float(playerscore - 25000) / 1000.0
                total_original_point = round(total_original_point, 1)
                highest_point = max(highest_point, playerscore)
            
        average_rank = float(first_place) + float(second_place) * 2.0 + float(third_place) * 3.0 + float(fourth_place) * 4.0
        if average_rank != 0:
            average_rank /= float(total_games)
            average_rank = round(average_rank, 2)

        total_score -= punishment

        total_score = round(total_score, 1)

        member_data.append({
            'team_name': Team.query.get(member.team_id).name,
            'name': member.name,
            'total_score': total_score,
            'total_original_point': total_original_point,
            'total_games': total_games,
            'average_rank': average_rank,
            'highest_point': highest_point,
            'first_place': first_place,
            'second_place': second_place,
            'third_place': third_place,
            'fourth_place': fourth_place,
            'punishment': punishment
        })
    return sorted(member_data, key=lambda x: (x['total_games'] != 0, x['total_score']), reverse=True)

@app.route('/game_details/<int:game_id>')
def game_details(game_id):
    game = Game.query.get(game_id)
    teams = []
    if game.rules == 'M-League团体赛':
        teams = team_ranking_table(game)
    members = member_ranking_table(game)
    tab = request.args.get('tab', 'home')  # 默认为赛事说明

    fileurl = 'timetable/' + str(game.id) + '.csv'

    data = []
    # 读取 CSV 文件
    with open(fileurl, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            data.append(row)

    default_template = "details.html"
    custom_template = str(game_id) + ".html"

    if os.path.exists(os.path.join(app.template_folder, custom_template)):
        return render_template(custom_template, game=game, tab=tab, teams=teams, members=members, data=data)
    else:
        return render_template(default_template, game=game, tab=tab, teams=teams, members=members, data=data)

# 添加访问 PDF 的路由
@app.route('/intro/<int:game_id>.pdf')
def send_pdf(game_id):
    return send_from_directory('intro', f'{game_id}.pdf')

# 添加访问 LOGO 的路由
@app.route('/logo/<int:game_id>.png')
def send_logo(game_id):
    return send_from_directory('logo', f'{game_id}.png')

@app.route('/add_team/<int:game_id>', methods=['POST'])
def add_team(game_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'team_management')

    team_name = request.form.get('team_name')
    new_team = Team(name=team_name, game_id=game_id)
    
    db.session.add(new_team)
    db.session.commit()
    
    return redirect(url_for('manage_game', game_id=game_id, tab=tab))

@app.route('/delete_team/<int:team_id>', methods=['POST'])
def delete_team(team_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'team_management')

    team = Team.query.get(team_id)
    if team:
        db.session.delete(team)
        db.session.commit()
        flash('队伍信息删除成功！', 'success')
    else:
        flash('队伍信息删除失败！', 'error')
    
    return redirect(url_for('manage_game', game_id=team.game_id, tab=tab))

@app.route('/edit_team/<int:team_id>', methods=['POST'])
def edit_team(team_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'team_management')

    team = Team.query.get(team_id)
    if team:
        team_name = request.form.get('team_name')
        team.name = team_name
        
        db.session.commit()
        flash('队伍信息编辑成功！', 'success')
    else:
        flash('队伍信息编辑失败！', 'error')
    
    return redirect(url_for('manage_game', game_id=team.game_id, tab=tab))

@app.route('/add_team_plan/<int:game_id>', methods=['POST'])
def add_team_plan(game_id):

    if not is_logged_in():  # 检查用户是否登录
        flash('你未登录或会话已超时，请登录！', 'warning')
        return redirect(url_for('login'))  # 未登录则重定向到登录页面
    
    tab = request.args.get('tab', 'schedule_input')

    east_team_id = request.form.get('east_team_id')
    south_team_id = request.form.get('south_team_id')
    west_team_id = request.form.get('west_team_id')
    north_team_id = request.form.get('north_team_id')

    team_ids = [east_team_id, south_team_id, west_team_id, north_team_id]

    if len(team_ids) != len(set(team_ids)):
        flash('选手不能重复，请重新选择！', 'error')
        return redirect(url_for('manage_game', game_id=game_id, tab=tab))

    new_plan = Plan(east_team_id=east_team_id, south_team_id=south_team_id, west_team_id=west_team_id, north_team_id=north_team_id)
    
    db.session.add(new_plan)
    flash('半庄计划添加成功！', 'success')
    db.session.commit()
    
    return redirect(url_for('manage_game', game_id=game_id, tab=tab))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)  # 运行服务器
