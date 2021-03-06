# -*- coding: utf-8 -*-

import os, json
from flask import Flask, app, render_template, request
from flask_login import login_user, login_required, logout_user, LoginManager, current_user

import settings
from src import common_util, cache, user_login, sql_manager, host_manager, user_manager

app = Flask("mysql_audit", instance_relative_config=True, instance_path=os.getcwd())
app.config["SESSION_COOKIE_NAME"] = "mysql_audit"
app.logger.debug('A value for debugging')
app.logger.warning('A warning occurred (%d apples)', 42)
app.logger.error('An error occurred')
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "login_home"
login_manager.init_app(app=app)
cache.MyCache().load_all_cache()


# region tab

@app.route("/main")
@login_required
def main():
    return render_template("main.html", user_info=cache.MyCache().get_user_info(current_user.id), administrator_role=settings.ROLE_ADMINISTRATOR)


@app.route("/home")
@login_required
def home():
    return render_template("home.html")


# endregion

# region sql audit

@app.route("/audit")
@login_required
def sql_audit():
    return render_template("audit.html", host_infos=sql_manager.get_audit_mysql_host())


@app.route("/audit/check", methods=["POST"])
@login_required
def get_sql_audit_info():
    return sql_manager.audit_sql(get_object_from_json_tmp(request.get_data()))


@app.route("/audit/check/<int:id>", methods=["GET", "POST"])
@login_required
def get_sql_audit_info_by_sql_id(id):
    return sql_manager.audit_sql_by_sql_id(id)


@app.route("/audit/db_names/<int:host_id>", methods=["GET", "POST"])
@login_required
def get_database_names(host_id):
    return sql_manager.get_database_names(host_id)


@app.route("/standard", methods=["GET", "POST"])
@login_required
def get_sql_standard():
    return render_template("sql_standard.html")


@app.route("/review/sql/work", methods=["POST"])
@login_required
def review_sql_work():
    return sql_manager.audit_sql_work(get_object_from_json_tmp(request.get_data()))


@app.route("/review/sql/work/remark/<int:sql_id>", methods=["POST", "GET"])
@login_required
def get_review_remark(sql_id):
    return sql_manager.get_audit_remark(sql_id)

# endregion

# region sql execute

@app.route("/execute")
@login_required
def sql_work():
    return render_template("sql_work_add.html",
                           host_infos=sql_manager.get_execute_mysql_host(),
                           dba_users=cache.MyCache().get_user_info_by_group_id(settings.DBA_GROUP_ID),
                           audit_user_infos=cache.MyCache().get_audit_user_infos())


@app.route("/execute/add", methods=["POST"])
@login_required
def add_sql_work():
    return sql_manager.add_sql_work(get_object_from_json_tmp(request.get_data()))


@app.route("/execute/delete/<int:id>")
@login_required
def delete_sql_work(id):
    return sql_manager.delete_sql_work(id)


@app.route("/execute/sql/execute/<int:id>", methods=["GET", "POST"])
@login_required
def get_sql_execute_home(id):
    return render_template("sql_execute.html", sql_info=sql_manager.get_sql_info_by_id(id))


@app.route("/execute/sql/execute/new/<int:id>", methods=["GET", "POST"])
@login_required
def get_sql_execute_home_new(id):
    return render_template("sql_execute_home.html", sql_info=sql_manager.get_sql_info_by_id(id), user_info=cache.MyCache().get_user_info(current_user.id))


@app.route("/execute/now/<int:sql_id>", methods=["GET", "POST"])
@login_required
def sql_execute_by_sql_id(sql_id):
    obj = get_object_from_json(request.form)
    obj.sql_id = sql_id
    return render_template("sql_execute_view.html", audit_infos=sql_manager.sql_execute(obj))


@app.route("/execute/result/<int:sql_id>", methods=["GET", "POST"])
@login_required
def get_sql_result(sql_id):
    return sql_manager.get_sql_result(sql_id)


@app.route("/execute/check/warnings/<int:sql_id>", methods=["GET", "POST"])
@login_required
def get_sql_audit_result_has_warnings(sql_id):
    return sql_manager.check_sql_audit_result_has_warnings(sql_id)


@app.route("/execute/rollback/sql/<int:sql_id>", methods=["GET", "POST"])
@login_required
def get_rollback_sql(sql_id):
    return json.dumps(sql_manager.get_rollback_sql(sql_id), default=lambda o: o.__dict__)


# endregion

# region sql list

# 工单列表主界面api
# 根据用户角色返回不同的界面
@app.route("/list")
@login_required
def sql_list_home():
    user_info = cache.MyCache().get_user_info(current_user.id)
    if (user_info.group_id == settings.DBA_GROUP_ID and user_info.role_id == settings.ROLE_DEV):
        return render_template("list_for_dba.html")
    if (user_info.role_id == settings.ROLE_DEV):
        return render_template("list_for_dev.html")
    if (user_info.role_id == settings.ROLE_LEADER):
        return render_template("list_for_leader.html")
    if (user_info.role_id == settings.ROLE_ADMINISTRATOR):
        return render_template("list_for_admin.html", user_infos=cache.MyCache().get_user_info(), sql_work_status=settings.SQL_WORK_STATUS_DICT)
    return render_template("list.html", user_infos=cache.MyCache().get_user_info(), sql_work_status=settings.SQL_WORK_STATUS_DICT)


# 工单列表查询接口
# 根据用户角色获取不同的数据
@app.route("/list/query", methods=["POST"])
@login_required
def query_sql_list():
    user_info = cache.MyCache().get_user_info(current_user.id)
    if (user_info.group_id == settings.DBA_GROUP_ID and user_info.role_id == settings.ROLE_DEV):
        obj = get_object_from_json_tmp(request.get_data())
        result_sql_list = sql_manager.get_sql_work_for_dba(obj)
    elif (user_info.role_id == settings.ROLE_DEV):
        obj = get_object_from_json_tmp(request.get_data())
        result_sql_list = sql_manager.get_sql_work_for_dev(obj)
    elif (user_info.role_id == settings.ROLE_LEADER):
        obj = get_object_from_json_tmp(request.get_data())
        result_sql_list = sql_manager.get_sql_work_for_leader(obj)
    else:
        obj = get_object_from_json(request.form)
        result_sql_list = sql_manager.get_sql_list(obj)
    return render_template("list_view.html",
                           sql_list=result_sql_list,
                           user_info=user_info,
                           page_number=obj.page_number,
                           page_list=get_page_number_list(obj.page_number),
                           min_id=get_min_id(result_sql_list, obj.page_number))


# 删除工单接口，只能删除自己创建的工单
@app.route("/list/delete/<int:sql_id>", methods=["GET", "POST"])
@login_required
def delete_sql_list(sql_id):
    return sql_manager.delete_sql_work(sql_id)


# 获取工单详情信息
@app.route("/sql/work/<int:sql_id>", methods=["GET", "POST"])
@login_required
def show_sql_work(sql_id):
    return render_template("work_show_template.html", sql_info=sql_manager.get_sql_info_by_id(sql_id))


# 获取分页数据list
def get_page_number_list(page_number):
    if (page_number <= 5):
        page_list = range(1, 10)
    else:
        page_list = range(page_number - 5, page_number + 6)
    return page_list


# 获取当前列表中的最小id，用于提高分页效率
def get_min_id(sql_list, page_number):
    if (page_number == 1 or sql_list == None or len(sql_list) <= 0):
        return 999999999
    else:
        number = 1
        lenght = len(sql_list)
        for info in sql_list:
            if (number == lenght):
                return info.id
            number += 1


# endregion

# region host api

@app.route("/host")
@login_required
def get_host():
    return render_template("host.html")


@app.route("/host/query", methods=["POST"])
@login_required
def query_host():
    return render_template("host_view.html", host_infos=host_manager.query_host_infos())


@app.route("/host/add", methods=["POST"])
@login_required
def add_host():
    return host_manager.add(get_object_from_json(request.form))


@app.route("/host/update", methods=["POST"])
@login_required
def update_host():
    return "update ok"


@app.route("/host/delete", methods=["POST"])
@login_required
def delete_host():
    host_manager.delete(get_object_from_json(request.form))
    return "delete mysql host ok!"


@app.route("/host/test", methods=["POST"])
@login_required
def test_connection():
    return host_manager.test_connection(get_object_from_json(request.form))


@app.route("/host/query/host_id", methods=["POST"])
@login_required
def get_host_info():
    return host_manager.get_host_info(get_object_from_json(request.form))


# endregion

# region user api

@app.route("/user")
@login_required
def get_user():
    return render_template("user.html",
                           role_infos=cache.MyCache().get_role_info(),
                           group_infos=cache.MyCache().get_group_info(),
                           host_infos=cache.MyCache().get_mysql_host_info())


@app.route("/user/add", methods=["GET", "POST"])
@login_required
def add_user():
    return user_manager.add_user(get_object_from_json_tmp(request.get_data()))


@app.route("/user/query", methods=["POST"])
@login_required
def query_user():
    return render_template("user_view.html", user_infos=user_manager.query_user(get_object_from_json_tmp(request.get_data())))


@app.route("/user/delete/<int:user_id>", methods=["GET", "POST"])
@login_required
def delete_user(user_id):
    message = user_manager.delete_user(user_id)
    logout()
    return message


@app.route("/user/start/<int:user_id>", methods=["GET", "POST"])
@login_required
def start_user(user_id):
    return user_manager.start_user(user_id)


@app.route("/user/group/add", methods=["POST"])
@login_required
def add_group():
    return user_manager.add_group_info(get_object_from_json_tmp(request.get_data()))


@app.route("/user/group/query", methods=["POST"])
@login_required
def query_group():
    return render_template("user_group_view.html", user_group_infos=user_manager.get_user_group_infos())


@app.route("/user/group/delete/<int:group_id>", methods=["POST"])
@login_required
def delete_group(group_id):
    return user_manager.delete_user_group_info(group_id)


@app.route("/user/group/update", methods=["POST"])
@login_required
def update_group():
    return user_manager.update_user_group_info(get_object_from_json_tmp(request.get_data()))


@app.route("/user/update/dialog/<int:user_id>", methods=["GET", "POST"])
@login_required
def get_show_update_user_dialog(user_id):
    return render_template("user_update_view.html",
                           role_infos=cache.MyCache().get_role_info(),
                           group_infos=cache.MyCache().get_group_info(),
                           user_info=cache.MyCache().get_user_info(user_id))


# endregion

# region sql work update

@app.route("/work/update/<int:sql_id>", methods=["GET", "POST"])
@login_required
def get_update_sql_work_html(sql_id):
    return render_template("sql_edit_home.html",
                           work_info=sql_manager.get_sql_info_by_id(sql_id),
                           host_infos=sql_manager.get_audit_mysql_host(),
                           dba_users=cache.MyCache().get_user_info_by_group_id(settings.DBA_GROUP_ID),
                           audit_user_infos=cache.MyCache().get_audit_user_infos())

    return render_template("sql_update_view.html",
                           work_info=sql_manager.get_sql_info_by_id(sql_id),
                           host_infos=sql_manager.get_audit_mysql_host(),
                           dba_users=cache.MyCache().get_user_info_by_group_id(settings.DBA_GROUP_ID),
                           audit_user_infos=cache.MyCache().get_audit_user_infos())


@app.route("/work/update/sql/save", methods=["GET", "POST"])
@login_required
def update_sql_work():
    return sql_manager.update_sql_work(get_object_from_json_tmp(request.get_data()))


# endregion

# region login api

@app.route("/login/verfiy", methods=['GET', 'POST'])
def login_verfiy():
    result = common_util.Entity()
    result.error = ""
    result.success = ""
    user_tmp = user_login.User(request.form["userName"])
    if (user_tmp.verify_password(request.form["passWord"], result) == True):
        login_user(user_tmp)
    return json.dumps(result, default=lambda o: o.__dict__)


@app.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return "ok"


@login_manager.user_loader
def load_user(user_id):
    return user_login.User(None).get(user_id)


@app.route("/login")
def login_home():
    return "<p hidden>login_error</p>" + render_template("login.html")


# endregion

# region commcon method

def get_object_from_json(json_value):
    obj = common_util.Entity()
    for key, value in dict(json_value).items():
        if (value[0].isdigit()):
            setattr(obj, key, int(value[0]))
        else:
            if (value[0] == "null"):
                setattr(obj, key, None)
            else:
                setattr(obj, key, value[0])
    obj.current_user_id = current_user.id
    return obj


def get_object_from_json_tmp(json_value):
    obj = common_util.Entity()
    for key, value in json.loads(json_value).items():
        if (str(value).isdigit()):
            setattr(obj, key, int(value))
        else:
            if (value == "null"):
                setattr(obj, key, None)
            else:
                setattr(obj, key, value)
    obj.current_user_id = current_user.id
    return obj


# endregion

# region run server

if __name__ == '__main__':
    port = 5200
    ip = "0.0.0.0"
    if (settings.LINUX_OS):
        print("linux start ok.")
        app.run(debug=False, host=ip, port=port, use_reloader=False, threaded=True)
    if (settings.WINDOWS_OS):
        print("windows start ok.")
        app.run(debug=True, host=ip, port=port, use_reloader=True, threaded=True)

# endregion
