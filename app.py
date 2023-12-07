import json

from flask import Flask, render_template, request, session, jsonify, Response
import pymysql
import os
from datetime import timedelta
import pandas as pd
import decimal
import datetime
import random
import string
from surprise import Dataset, Reader, KNNBasic
from surprise.model_selection import cross_validate, train_test_split
from surprise.accuracy import rmse

app = Flask(__name__)
app.secret_key = os.urandom(24)  # random session key
app.permanent_session_lifetime = timedelta(minutes=60)  # session time

db_config = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": 'root',
    "passwd": "",
    "db": 'gym'
}


#
# class DecimalEncoder(json.JSONEncoder):
#     def default(self, o):
#         if isinstance(o, Decimal):
#             return float(o)
#         return super(DecimalEncoder, self).default(o)

@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    else:
        user = request.form.get("email")
        password = request.form.get("password")
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        cursor.execute("select * from Customers where Email = %s and Password = %s", [user, password, ])
        # cursor.execute("select * from admin where id > %s", [2, ])
        data_list = cursor.fetchall()
        cursor.close()
        conn.close()

        if len(data_list) == 0:
            return render_template("login.html", data_list=[{"errorMessage": "Email or Password error"}])
        else:
            session.permanent = True
            session['EmployeeID'] = None
            session['EmployeeTypeID'] = None

            session['CustomerID'] = data_list[0]['CustomerID']
            session['Username'] = data_list[0]['Name']
        return render_template("my_info.html", data_list=data_list)


@app.route("/login_employee", methods=['GET', 'POST'])
def login_employee():
    if request.method == 'GET':
        return render_template("login_employee.html")
    else:
        user = request.form.get("email")
        password = request.form.get("password")
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        cursor.execute("select * from Employees where Email = %s and Password = %s", [user, password, ])
        # cursor.execute("select * from admin where id > %s", [2, ])
        data_list = cursor.fetchall()
        cursor.close()
        conn.close()

        if len(data_list) == 0:
            return render_template("login_employee.html", data_list=[{"errorMessage": "Email or Password error"}])
        else:
            session.permanent = True
            session['CustomerID'] = None
            session['EmployeeID'] = data_list[0]['EmployeeID']
            # print(data_list)
            session['Username'] = data_list[0]['EmployeeName']
            session['EmployeeTypeID'] = data_list[0]['EmployeeTypeID']  # Type=3 admin

            data_list_employeetypes = list_employeetype_info()
            data_list_stores = list_store_info()
        return render_template("edit_employee.html", data_list=data_list,
                               data_list_employeetypes=data_list_employeetypes, data_list_stores=data_list_stores)

@app.route("/delete_employee", methods=['POST'])
def delete_employee():
    idEmployee = request.form.get("OperationalEmployeeID")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = "UPDATE Stores Set ManagerID = Null WHere ManagerID = %s "
    cursor.execute(sql, [idEmployee, ])
    sql = "Delete from Employees where EmployeeID = %s "
    cursor.execute(sql, [idEmployee, ])
    conn.commit()
    cursor.close()
    conn.close()

    return search_employee()

@app.route("/edit_employee", methods=['GET', 'POST'])
def edit_employee():
    idStore = None
    idEmployee = request.form.get("EmployeeID")
    sEmployeeNamee = request.form.get("EmployeeName")
    sEmployeeType = request.form.get("EmployeeType")
    sJobTitle = request.form.get("JobTitle")
    if request.form.get("Store") != "":
        idStore = request.form.get("Store")
    sEmail = request.form.get("Email")
    sPassword = request.form.get("Password")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = "Update Employees set EmployeeName = %s, EmployeeTypeID = %s, Email = %s, Password = %s, StoreAssignedID = %s, JobTitle = %s where EmployeeID = %s "
    cursor.execute(sql,
                   [sEmployeeNamee, sEmployeeType, sEmail, sPassword, idStore, sJobTitle, idEmployee])
    conn.commit()
    cursor.close()
    conn.close()

    return search_employee()

@app.route("/employee/editform", methods=['POST'])
def editform_employee():
    idEmployee = request.form.get("OperationalEmployeeID")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if idEmployee != "":
        sWhere = str(sWhere) + " And EmployeeID = " + str(idEmployee)

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = (" SELECT E.*, ET.EmployeeTypeName, S.StoreName "
           " from Employees E "
           " left join EmployeeTypes ET ON E.EmployeeTypeID = ET.EmployeeTypeID "
           " left join Stores S ON S.StoreID = E.StoreAssignedID ") + str(sWhere)

    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    data_list_employeetypes = list_employeetype_info()
    data_list_stores = list_store_info()
    return render_template("edit_employee.html", data_list=data_list,
                       data_list_employeetypes=data_list_employeetypes, data_list_stores=data_list_stores)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        sName = request.form.get("Name")
        sStreet = request.form.get("Street")
        sCity = request.form.get("City")
        sZipcode = request.form.get("Zipcode")
        sEmail = request.form.get("Email")
        sPassword = request.form.get("Password")
        sKind = request.form.get("Kind")
        sPhoneNumber = request.form.get("PhoneNumber")
        sMarriageStatus = None
        sGender = None
        sBirthDate = None
        mAnnualIncome = None
        sBusinessCategory = None
        mCompanyGrossAnnualIncome = None
        if sKind == "home":
            sMarriageStatus = request.form.get("MarriageStatus")
            sGender = request.form.get("Gender")
            if request.form.get("BirthDate") != "":
                sBirthDate = pd.to_datetime(request.form.get("BirthDate"))
            if request.form.get("AnnualIncome") != "":
                mAnnualIncome = request.form.get("AnnualIncome")
        else:
            sBusinessCategory = request.form.get("BusinessCategory")
            mCompanyGrossAnnualIncome = request.form.get("CompanyGrossAnnualIncome")

        # 1. 连接数据库
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        # 2. 执行语句
        sql = "insert into Customers(Name, Street, City, Zipcode, Email, Password, Kind, MarriageStatus, Gender, BirthDate, AnnualIncome, BusinessCategory, CompanyGrossAnnualIncome, PhoneNumber) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql,
                       [sName, sStreet, sCity, sZipcode, sEmail, sPassword, sKind, sMarriageStatus, sGender, sBirthDate,
                        mAnnualIncome, sBusinessCategory, mCompanyGrossAnnualIncome, sPhoneNumber])
        conn.commit()
        # 3. 关闭数据库连接
        cursor.close()
        conn.close()

        return render_template("login.html")


@app.route("/add_class", methods=["GET", "POST"])
def add_class():
    if request.method == "GET":
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        cursor.execute("select * from coursetypes")
        data_list_coursetypes = cursor.fetchall()
        # print(data_list_coursetypes)
        cursor.execute("select * from stores")
        data_list_stores = cursor.fetchall()
        # print(data_list_stores)
        cursor.execute("select * from employees where employeetypeid='1'")
        data_list_trainers = cursor.fetchall()
        # print(data_list_trainers)
        cursor.close()
        conn.close()
        return render_template("add_class.html", data_list_coursetypes=data_list_coursetypes,
                               data_list_stores=data_list_stores, data_list_trainers=data_list_trainers)
    else:
        sCourseName = request.form.get("CourseName")
        sCourseType = request.form.get("CourseType")
        sCourseDescription = request.form.get("CourseDescription")

        if request.form.get("StartDate") != "":
            sStartDate = pd.to_datetime(request.form.get("StartDate"))
        else:
            sStartDate = None
        if request.form.get("EndDate") != "":
            sEndDate = pd.to_datetime(request.form.get("EndDate"))
        else:
            sEndDate = None

        sTrainer = request.form.get("Trainer")
        sStore = request.form.get("Store")
        sMaximumSlots = request.form.get("MaximumSlots")
        sPrice = request.form.get("Price")
        # print(sCourseName,sCourseType,sCourseDescription,sStartDate,sEndDate,sTrainer,sStore,sMaximumSlots,sPrice)

        # 1. 连接数据库
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        # 2. 执行语句
        sql = "insert into Courses(CourseName, CourseType, CourseDescription, StartDate, EndDate, TrainerID, StoreID, MaximumSlots, Price) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, [sCourseName, sCourseType, sCourseDescription, sStartDate, sEndDate, sTrainer, sStore,
                             sMaximumSlots, sPrice])
        conn.commit()
        # 3. 关闭数据库连接
        cursor.close()
        conn.close()

        return search_class()


@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if request.method == "GET":
        data_list_employeetypes = list_employeetype_info()
        data_list_stores = list_store_info()
        return render_template("add_employee.html", data_list_employeetypes=data_list_employeetypes,
                               data_list_stores=data_list_stores)
    else:
        idStore = None
        sEmployeeNamee = request.form.get("EmployeeName")
        sEmployeeType = request.form.get("EmployeeType")
        sJobTitle = request.form.get("JobTitle")
        if request.form.get("Store") != "":
            idStore = request.form.get("Store")
        sEmail = request.form.get("Email")
        sPassword = request.form.get("Password")

        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        sql = "insert into Employees(EmployeeName, EmployeeTypeID, Email, Password, StoreAssignedID, JobTitle) values (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, [sEmployeeNamee, sEmployeeType, sEmail, sPassword, idStore, sJobTitle])
        conn.commit()
        cursor.close()
        conn.close()

        return search_employee()

@app.route("/search_employee")
def search_employee():
    sEmployeeName = ""
    if request.args.get("SearchEmployeeName") != None:
        sEmployeeName = request.args.get("SearchEmployeeName")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if sEmployeeName != "":
        sWhere = str(sWhere) + " And E.EmployeeName Like '%" + str(sEmployeeName) + "%'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = (" SELECT E.*, ET.EmployeeTypeName, S.StoreName "
           " from Employees E "
           " left join EmployeeTypes ET ON E.EmployeeTypeID = ET.EmployeeTypeID "
           " left join Stores S ON S.StoreID = E.StoreAssignedID ") + str(sWhere)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("search_employee.html", data_list=data_list, SearchEmployeeName=sEmployeeName)


@app.route("/start_header_bottom")
def start_header_bottom():
    return render_template("start_header_bottom.html")


@app.route("/start_menu")
def start_menu():
    return render_template("start_menu.html")


@app.route("/footer_bottom")
def footer_bottom():
    return render_template("footer_bottom.html")


@app.route("/search_class")
def search_class():
    sCourseName = ""
    sCourseType = ""
    sArrange = ""

    if request.args.get("SearchCourseName") != None:
        sCourseName = request.args.get("SearchCourseName")

    if request.args.get("SearchCourseType") != None:
        sCourseType = request.args.get("SearchCourseType")

    if request.args.get("SearchArrange") != None:
        sArrange = request.args.get("SearchArrange")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    sOrderby = ""
    if sCourseName != "":
        sWhere = str(sWhere) + " And CourseName Like '%" + str(sCourseName) + "%'"

    if sCourseType != "":
        sWhere = str(sWhere) + " And C.CourseType = " + str(sCourseType)

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    if sArrange != "":
        sOrderby = " ORDER BY " + str(sArrange)

    sql = (
              "select C.*, C.CourseName, E.EmployeeName, S.StoreName,CT.CourseTypeName, COALESCE(T.OccupiedSlots,0) OccupiedSlots from Courses C "
              "left join CourseTypes CT on C.CourseType = CT.CourseTypeID "
              "left join Employees E on C.TrainerID = E.EmployeeID "
              "left join Stores S on C.StoreID = S.StoreID "
              "left join (select CourseID, sum(quantity) OccupiedSlots from transactions group by CourseID) T "
              "on C.CourseID = t.CourseID") + str(sWhere) + str(sOrderby)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    data_list_coursetypes = list_coursetype_info()
    data_list_arrangeby = list_arrangeby_class_info()
    return render_template("search_class.html", data_list=data_list, SearchCourseName=sCourseName,
                           data_list_coursetypes=data_list_coursetypes, SearchCourseType=sCourseType,
                           data_list_arrangeby=data_list_arrangeby, SearchArrange=sArrange)


@app.route("/delete_class", methods=['POST'])
def delete_class():
    idCourse = request.form.get("OperationalCourseID")
    # print(idCourse)
    # # 1. 连接数据库
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    # 2. 执行语句
    sql = "Delete from Courses where CourseID = %s "
    cursor.execute(sql, [idCourse, ])
    conn.commit()
    # 3. 关闭数据库连接
    cursor.close()
    conn.close()

    return search_class()


@app.route("/edit_class", methods=['GET', 'POST'])
def edit_class():
    idCourse = request.form.get("CourseID")
    sCourseName = request.form.get("CourseName")
    if request.form.get("CourseType") != "":
        idCourseType = request.form.get("CourseType")
    else:
        idCourseType = None
    sCourseDescription = request.form.get("CourseDescription")
    if request.form.get("StartDate") != "":
        sStartDate = pd.to_datetime(request.form.get("StartDate"))
    else:
        sStartDate = None
    if request.form.get("EndDate") != "":
        sEndDate = pd.to_datetime(request.form.get("EndDate"))
    else:
        sEndDate = None
    if request.form.get("Trainer") != "":
        idTrainer = request.form.get("Trainer")
    else:
        idTrainer = None
    if request.form.get("Store") != "":
        iStore = request.form.get("Store")
    else:
        iStore = None
    iMaximumSlots = request.form.get("MaximumSlots")
    iPrice = request.form.get("Price")
    # print(sCourseName,sCourseType,sCourseDescription,sStartDate,sEndDate,sTrainer,sStore,sMaximumSlots,sPrice)

    # 1. 连接数据库
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    # 2. 执行语句
    sql = "Update Courses set CourseName = %s, CourseType = %s, CourseDescription = %s, StartDate = %s, EndDate = %s, TrainerID = %s, StoreID = %s, MaximumSlots = %s, Price = %s where CourseID = %s "
    cursor.execute(sql,
                   [sCourseName, idCourseType, sCourseDescription, sStartDate, sEndDate, idTrainer, iStore,
                    iMaximumSlots, iPrice, idCourse])
    conn.commit()
    # 3. 关闭数据库连接
    cursor.close()
    conn.close()

    return search_class()


@app.route("/class/editform", methods=['POST'])
def editform_class():
    idCourse = request.form.get("OperationalCourseID")
    # print(idCourse)
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if idCourse != "":
        sWhere = str(sWhere) + " And CourseID = " + str(idCourse)

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = ("select C.*, C.CourseName, E.EmployeeName, S.StoreName,CT.CourseTypeName from Courses C "
           "left join CourseTypes CT on C.CourseType = CT.CourseTypeID "
           "left join Employees E on C.TrainerID = E.EmployeeID "
           "left join Stores S on C.StoreID = S.StoreID ") + str(sWhere)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    data_list_stores = list_store_info()
    data_list_trainers = list_trainer_info()
    data_list_coursetypes = list_coursetype_info()
    # print(data_list_coursetypes)
    return render_template("edit_class.html", data_list=data_list, data_list_stores=data_list_stores,
                           data_list_trainers=data_list_trainers, data_list_coursetypes=data_list_coursetypes)


@app.route("/class/Signupform", methods=['POST'])
def Signupform_class():
    idCourse = request.form.get("OperationalCourseID")
    # print(idCourse)
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if idCourse != "":
        sWhere = str(sWhere) + " And C.CourseID = " + str(idCourse)

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = (
              "select C.*, C.CourseName, E.EmployeeName, S.StoreName,CT.CourseTypeName, COALESCE(T.OccupiedSlots,0) OccupiedSlots from Courses C "
              "left join CourseTypes CT on C.CourseType = CT.CourseTypeID "
              "left join Employees E on C.TrainerID = E.EmployeeID "
              "left join Stores S on C.StoreID = S.StoreID "
              "left join (select CourseID, sum(quantity) OccupiedSlots from transactions group by CourseID) T "
              "on C.CourseID = t.CourseID") + str(sWhere)

    print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    data_list_salespersons = list_salesperson_info()
    data_list_stores = list_store_info()
    data_list_trainers = list_trainer_info()
    return render_template("signup_class.html", data_list=data_list, data_list_salespersons=data_list_salespersons,
                           data_list_stores=data_list_stores, data_list_trainers=data_list_trainers)


@app.route("/signup_class", methods=["POST"])
def signup_class():
    current_time = datetime.datetime.now()
    sOrderNumber = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    dtOrder = pd.to_datetime(current_time)
    idSalesperson = request.form.get("Salesperson")
    idCourse = request.form.get("CourseID")
    iQuantity = request.form.get("Quantity")
    mPurchaseAmount = request.form.get("TotalPrice")
    # print(mPurchaseAmount)
    idCustomer = session.get("CustomerID")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from courses where courseid = %s "
    cursor.execute(sql, [idCourse, ])
    data = cursor.fetchall()
    for item in data:
        sCourseName = item["CourseName"]

    sql = "insert into Transactions(OrderNumber, OrderDate, SalespersonID, CourseID, CourseName, Quantity, PurchaseAmount, CustomerID) values (%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor.execute(sql,
                   [sOrderNumber, dtOrder, idSalesperson, idCourse, sCourseName, iQuantity, mPurchaseAmount, idCustomer])
    conn.commit()
    cursor.close()
    conn.close()

    return search_my_order()


@app.route("/search_store")
def search_store():
    sStoreName = ""
    if request.args.get("SearchStoreName") != None:
        sStoreName = request.args.get("SearchStoreName")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if sStoreName != "":
        sWhere = str(sWhere) + " And StoreName Like '%" + str(sStoreName) + "%'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = (" select S.*, E.EmployeeName as ManagerName, R.RegionName "
           " from Stores S "
           " left join Employees E on S.ManagerID = E.EmployeeID "
           " left join Regions R on S.RegionID = R.RegionID ") + str(sWhere)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    print(data_list)
    cursor.close()
    conn.close()

    return render_template("search_store.html", data_list=data_list, SearchCourseName=sStoreName)


@app.route("/add_store", methods=["GET", "POST"])
def add_store():
    if request.method == "GET":
        data_list_managers = list_salesperson_info()
        data_list_regions = list_region_info()
        return render_template("add_store.html", data_list_managers=data_list_managers,
                               data_list_regions=data_list_regions)
    else:
        sStoreName = request.form.get("StoreName")
        sAddress = request.form.get("Address")
        sManagerID = None
        sRegionID = None
        if request.form.get("ManagerID") != "":
            sManagerID = request.form.get("ManagerID")
        if request.form.get("RegionID") != "":
            sRegionID = request.form.get("RegionID")

        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        sql = "insert into Stores(StoreName, Address, ManagerID, RegionID) values (%s, %s, %s, %s)"
        cursor.execute(sql, [sStoreName, sAddress, sManagerID, sRegionID])
        conn.commit()

        cursor.close()
        conn.close()
        return search_store()


@app.route("/store/editform", methods=['POST'])
def editform_store():
    idStore = request.form.get("OperationalStoreID")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if idStore != "":
        sWhere = str(sWhere) + " And S.StoreID = " + str(idStore)

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = (" select S.*, E.EmployeeName as ManagerName, R.RegionName "
           " from Stores S "
           " left join Employees E on S.ManagerID = E.EmployeeID "
           " left join Regions R on S.RegionID = R.RegionID ") + str(sWhere)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    data_list_managers = list_salesperson_info()
    # print(data_list_managers)
    data_list_regions = list_region_info()
    return render_template("edit_store.html", data_list=data_list, data_list_managers=data_list_managers,
                           data_list_regions=data_list_regions)


@app.route("/edit_store", methods=['GET', 'POST'])
def edit_store():
    idStore = request.form.get("StoreID")
    sStoreName = request.form.get("StoreName")
    sAddress = request.form.get("Address")
    idManager = None
    idRegion = None
    if request.form.get("ManagerID") != "":
        idManager = request.form.get("ManagerID")
    if request.form.get("RegionID") != "":
        idRegion = request.form.get("RegionID")

    # 1. 连接数据库
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    # 2. 执行语句
    sql = "Update Stores set StoreName = %s, Address = %s, ManagerID = %s, RegionID = %s where StoreID = %s "
    cursor.execute(sql,
                   [sStoreName, sAddress, idManager, idRegion, idStore])
    conn.commit()
    # 3. 关闭数据库连接
    cursor.close()
    conn.close()

    return search_store()


@app.route("/delete_store", methods=['POST'])
def delete_store():
    idStore = request.form.get("OperationalStoreID")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = "Delete from Stores where StoreID = %s "
    cursor.execute(sql, [idStore, ])
    conn.commit()
    cursor.close()
    conn.close()

    return search_store()


@app.route("/dashboard/productcategories_sales")
def productcategories_sales():
    return render_template("productcategories_sales.html")


@app.route("/dashboard/productcategories_sales/get_data")
def productcategories_sales_get_data():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = ("SELECT CourseTypeName,sum(quantity) as Sales FROM Transactions T "
           "left join courses C on T.CourseID = C.courseid "
           "left join coursetypes CT on C.CourseType = CT.CourseTypeid "
           "group by CT.CourseTypeName")

    # print(sql)
    cursor.execute(sql)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    # print(data)
    data_xAxis = []
    data_yAxis = []
    for item in data:
        data_xAxis.append(item['CourseTypeName'])
        # 解决decimal的类型 无法进行json serialize的问题
        sales = str(decimal.Decimal(item['Sales']).quantize(decimal.Decimal('0')))
        data_yAxis.append(sales)
    data_list = {}
    data_list['xAxis'] = data_xAxis
    data_list['yAxis'] = data_yAxis

    return Response(json.dumps(data_list), mimetype="application/json")


@app.route("/dashboard/regions_sales")
def regions_sales():
    sStartDate = ""
    sEndDate = ""
    if request.args.get("StartDate") != None:
        sStartDate = request.args.get("StartDate")

    if request.args.get("EndDate") != None:
        sEndDate = request.args.get("EndDate")

    sWhere = ""
    if sStartDate != "":
        sWhere = str(sWhere) + " And T.OrderDate >= '" + str(sStartDate) + "'"

    if sEndDate != "":
        sWhere = str(sWhere) + " And T.OrderDate <= '" + str(sEndDate) + "'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = (" select R.RegionID, R.RegionName, sum(T.Quantity) TotalQuantity, sum(T.PurchaseAmount) TotalAmount "
           " from Transactions T left join Courses C on T.CourseID = C.CourseID "
           " left join Stores S on C.StoreID = S.StoreID "
           " left join Regions R on R.RegionID = S.RegionID " + str(sWhere) +
           " GROUP BY R.RegionID, R.RegionName ")
    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    # print(data_list)
    sumQuantity = 0
    sumAmount = 0
    for item in data_list:
        if item['TotalQuantity'] != None:
            sumQuantity = sumQuantity + item['TotalQuantity']
        if item['TotalAmount'] != None:
            sumAmount = sumAmount + item['TotalAmount']

    # print(data_list)
    return render_template("regions_sales.html", data_list=data_list, StartDate=sStartDate, EndDate=sEndDate,
                           sumQuantity=sumQuantity, sumAmount=sumAmount)


@app.route("/dashboard/daily_sales")
def daily_sales():
    sStartDate = ""
    sEndDate = ""
    if request.args.get("StartDate") != None:
        sStartDate = request.args.get("StartDate")

    if request.args.get("EndDate") != None:
        sEndDate = request.args.get("EndDate")

    sWhere = ""
    if sStartDate != "":
        sWhere = str(sWhere) + " And T.OrderDate >= '" + str(sStartDate) + "'"

    if sEndDate != "":
        sWhere = str(sWhere) + " And T.OrderDate <= '" + str(sEndDate) + "'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = (" select DATE_FORMAT(T.OrderDate, '%Y-%m-%d') OrderDate, sum(T.Quantity) TotalQuantity, sum(T.PurchaseAmount) TotalAmount "
           " from Transactions T left join Courses C on T.CourseID = C.CourseID "
           " left join Stores S on C.StoreID = S.StoreID "
           " left join Regions R on R.RegionID = S.RegionID " + str(sWhere) +
           " GROUP BY DATE_FORMAT(T.OrderDate, '%Y-%m-%d')  ")
    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    # print(data_list)
    sumQuantity = 0
    sumAmount = 0
    for item in data_list:
        if item['TotalQuantity'] != None:
            sumQuantity = sumQuantity + item['TotalQuantity']
        if item['TotalAmount'] != None:
            sumAmount = sumAmount + item['TotalAmount']

    # print(sumQuantity)
    return render_template("daily_sales.html", data_list=data_list, StartDate=sStartDate, EndDate=sEndDate,
                           sumQuantity=sumQuantity, sumAmount=sumAmount)


@app.route("/dashboard/business_purchase_sales")
def business_purchase_sales():
    sStartDate = ""
    sEndDate = ""
    if request.args.get("StartDate") != None:
        sStartDate = request.args.get("StartDate")

    if request.args.get("EndDate") != None:
        sEndDate = request.args.get("EndDate")

    sWhere = " And C.kind = 'business' "
    if sStartDate != "":
        sWhere = str(sWhere) + " And T.OrderDate >= '" + str(sStartDate) + "'"

    if sEndDate != "":
        sWhere = str(sWhere) + " And T.OrderDate <= '" + str(sEndDate) + "'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = ("select C.CustomerID, C.Name, sum(T.Quantity) TotalQuantity, sum(T.PurchaseAmount) TotalAmount "
           " from Transactions T left join Customers C on T.CustomerID = C.CustomerID " + str(sWhere) +
           " GROUP BY C.CustomerID, C.Name order by sum(T.Quantity) desc ")
    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    # print(data_list)
    sumQuantity = 0
    sumAmount = 0
    for item in data_list:
        if item['TotalQuantity'] != None:
            sumQuantity = sumQuantity + item['TotalQuantity']
        if item['TotalAmount'] != None:
            sumAmount = sumAmount + item['TotalAmount']

    # print(sumQuantity)
    return render_template("businesspurchase_sales.html", data_list=data_list, StartDate=sStartDate, EndDate=sEndDate,
                           sumQuantity=sumQuantity, sumAmount=sumAmount)


@app.route('/my/order')
def search_my_order():
    idCustomer = session.get("CustomerID")
    sCourseName = request.args.get("SearchCourseName")
    # print(sCourseName)
    data_list = search_order(idCustomer, sCourseName)

    return render_template("my_order.html", data_list=data_list)


def search_order(idCustomer, sCourseName):
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if idCustomer != None:
        sWhere = str(sWhere) + " And T.CustomerID = " + str(idCustomer)

    if sCourseName != None:
        sWhere = str(sWhere) + " And C.CourseName Like '%" + str(sCourseName) + "%'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = ("select T.*, T.salespersonname as employeename, Cu.name as CustomerName "
           "from transactions T "
           "left join Customers Cu ON T.CustomerID = Cu.CustomerID ") + str(sWhere)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return data_list


# yiming tian
@app.route("/search_region")
def search_region():
    sRegionName = ""
    if request.args.get("SearchRegionName") is not None:
        sRegionName = request.args.get("SearchRegionName")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if sRegionName != "":
        sWhere = str(sWhere) + " And RegionName Like '%" + str(sRegionName) + "%'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = "SELECT R.*, E.EmployeeName AS RegionManager FROM Regions R left join Employees E on E.EmployeeID = R.RegionManagerID " + str(
        sWhere)

    cursor.execute(sql)
    data_list = cursor.fetchall()
    # print(data_list)
    cursor.close()
    conn.close()
    return render_template("search_region.html", data_list=data_list, SearchRegionName=sRegionName)


@app.route("/add_region", methods=["GET", "POST"])
def add_region():
    if request.method == "GET":
        data_list_managers = list_salesperson_info()
        return render_template("add_region.html", data_list_managers=data_list_managers)
    else:
        # For submission
        sRegionName = request.form.get("RegionName")
        if request.form.get("RegionManagerID") == "":
            sRegionManagerID = None
        else:
            sRegionManagerID = request.form.get("RegionManagerID")
        # print(sRegionName)
        # Connect Database
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
        sql = "insert into Regions(RegionName, RegionManagerID) values (%s, %s)"
        cursor.execute(sql, [sRegionName, sRegionManagerID])
        conn.commit()

        cursor.close()
        conn.close()
        return render_template("success_page.html", message="Region added successfully")


@app.route("/delete_region", methods=['POST'])
def delete_region():
    idRegion = request.form.get("OperationalRegionID")
    # Connect Database
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = "DELETE FROM Stores WHERE RegionID = %s"
    cursor.execute(sql, [idRegion, ])
    sql = "DELETE FROM Regions WHERE RegionID = %s"
    cursor.execute(sql, [idRegion, ])
    conn.commit()
    cursor.close()
    conn.close()
    return search_region()


@app.route("/search_customer", methods=['GET', 'POST'])
def search_customer():
    sCustomerName = ""
    sCustomerType = ""
    if request.args.get("SearchCustomerName") != None:
        sCustomerName = request.args.get("SearchCustomerName")

    if request.args.get("SearchCustomerType") != None:
        sCustomerType = request.args.get("SearchCustomerType")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if sCustomerName != "":
        sWhere = str(sWhere) + " And Name Like '%" + str(sCustomerName) + "%'"

    if sCustomerType != "":
        sWhere = str(sWhere) + " And Kind = '" + str(sCustomerType) + "'"

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = ("select C.* from Customers C ") + str(sWhere)

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    data_list_customertypes = list_customertype_info()
    return render_template("search_customer.html", data_list=data_list, SearchCustomerName=sCustomerName,
                           SearchCustomerType=sCustomerType, data_list_customertypes=data_list_customertypes)


@app.route("/customer/editform", methods=['POST'])
def editform_customer():
    idCustomer = request.form.get("OperationalCustomerID")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sWhere = ""
    if idCustomer != "":
        sWhere = str(sWhere) + " And CustomerID = " + str(idCustomer)

    if sWhere != "":
        sWhere = " WHERE " + str(sWhere[5:])

    sql = ("select C.* from Customers C") + str(sWhere)

    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    data_list_customertypes = list_customertype_info()
    data_list_marriagestatus = list_marriagestatus_info()
    data_list_genders = list_gender_info()
    return render_template("edit_customer.html", data_list=data_list, data_list_customertypes=data_list_customertypes,
                           data_list_marriagestatus=data_list_marriagestatus, data_list_genders=data_list_genders)


@app.route("/edit_customer", methods=['GET', 'POST'])
def edit_customer():
    idCustomer = request.form.get("CustomerID")
    sName = request.form.get("Name")
    sStreet = request.form.get("Street")
    sCity = request.form.get("City")
    sZipcode = request.form.get("Zipcode")
    sEmail = request.form.get("Email")
    sPassword = request.form.get("Password")
    sKind = request.form.get("Kind")
    sPhoneNumber = request.form.get("PhoneNumber")
    sMarriageStatus = None
    sGender = None
    sBirthDate = None
    mAnnualIncome = None
    sBusinessCategory = None
    mCompanyGrossAnnualIncome = None
    if sKind == "home":
        sMarriageStatus = request.form.get("MarriageStatus")
        sGender = request.form.get("Gender")
        if request.form.get("BirthDate") != "":
            sBirthDate = pd.to_datetime(request.form.get("BirthDate"))
        if request.form.get("AnnualIncome") != "":
            mAnnualIncome = request.form.get("AnnualIncome")
    else:
        sBusinessCategory = request.form.get("BusinessCategory")
        mCompanyGrossAnnualIncome = request.form.get("CompanyGrossAnnualIncome")

    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = "Update Customers set Name = %s, Street = %s, City = %s, Zipcode = %s, Email = %s, Password = %s, Kind = %s, MarriageStatus = %s, Gender = %s, BirthDate = %s, AnnualIncome = %s, BusinessCategory = %s, CompanyGrossAnnualIncome = %s, PhoneNumber = %s where CustomerID = %s "
    cursor.execute(sql,
                   [sName, sStreet, sCity, sZipcode, sEmail, sPassword, sKind, sMarriageStatus, sGender, sBirthDate,
                    mAnnualIncome, sBusinessCategory, mCompanyGrossAnnualIncome, sPhoneNumber, idCustomer])
    conn.commit()
    cursor.execute("select * from Customers where CustomerID = %s", [idCustomer, ])
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_info.html", data_list=data_list)


@app.route("/delete_customer", methods=['POST'])
def delete_customer():
    idCustomer = request.form.get("OperationalCustomerID")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = "Delete from Customers where CustomerID = %s "
    cursor.execute(sql, [idCustomer, ])
    conn.commit()
    cursor.close()
    conn.close()

    return search_customer()


@app.route("/is_exist_email", methods=['GET', 'POST'])
def is_exist_email():
    sEmail = request.args.get("Email")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = " Select * from customers where Email = %s "
    cursor.execute(sql, [sEmail, ])
    conn.commit()
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    # print(data)
    data_list = {}
    data_list['Isvalid'] = True
    for item in data:
        data_list['Isvalid'] = False
    # print(data_list)
    return Response(json.dumps(data_list), mimetype="application/json")


@app.route("/is_exist_phonenumber", methods=['GET', 'POST'])
def is_exist_phonenumber():
    sPhoneNumber = request.args.get("PhoneNumber")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)
    sql = " Select * from customers where PhoneNumber = %s "
    cursor.execute(sql, [sPhoneNumber, ])
    conn.commit()
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    # print(data)
    data_list = {}
    data_list['Isvalid'] = True
    for item in data:
        data_list['Isvalid'] = False
    # print(data_list)
    return Response(json.dumps(data_list), mimetype="application/json")


# 自定义过滤器
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    if value:
        return value.strftime(format)
    else:
        return ""


# 组件内容返回
def list_store_info():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from stores"

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_list


def list_trainer_info():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from employees where employeetypeid = 1"

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_list


def list_coursetype_info():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from coursetypes"

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_list


def list_salesperson_info():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from employees where employeetypeid = 2"

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_list


def list_employeetype_info():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from employeetypes"

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_list


def list_region_info():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(cursor=pymysql.cursors.DictCursor)

    sql = "select * from regions"

    # print(sql)
    cursor.execute(sql)
    data_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return data_list


def list_customertype_info():
    data_list = [{'CustomerTypeID': 'home', 'CustomerTypeName': 'home'},
                 {'CustomerTypeID': 'business', 'CustomerTypeName': 'Business'}]
    return data_list


def list_marriagestatus_info():
    data_list = [{'MarriageStatusID': 'N', 'MarriageStatusName': 'N'},
                 {'MarriageStatusID': 'Y', 'MarriageStatusName': 'Y'}]
    return data_list


def list_gender_info():
    data_list = [{'GenderID': 'F', 'GenderName': 'F'}, {'GenderID': 'M', 'GenderName': 'M'}]
    return data_list


def list_arrangeby_class_info():
    data_list = [{'ArrangeByID': 'StartDate', 'ArrangeByName': 'StartDate'},
                 {'ArrangeByID': 'Price', 'ArrangeByName': 'Price'}]
    return data_list


# recommendation
@app.route("/recommendation", methods=['GET', 'POST'])
def recommendation():
    data_orders = search_order(None, None)
    data_user_id = []
    data_exercise_id = []
    data_rate = []
    for order in data_orders:
        data_user_id.append(order["CustomerID"])
        data_exercise_id.append(order["CourseName"])
        data_rate.append(random.randint(1, 5))
    data = {
        'user_id': data_user_id,
        'exercise_id': data_exercise_id,
        'rating': data_rate
    }
    df = pd.DataFrame(data)
    reader = Reader(rating_scale=(1, 5))
    dataset = Dataset.load_from_df(df[['user_id', 'exercise_id', 'rating']], reader)
    sim_options = {
        'name': 'cosine',
        'user_based': True
    }
    # Create a KNN model
    model = KNNBasic(sim_options=sim_options)
    # Split the dataset into training and testing sets
    trainset, testset = train_test_split(dataset, test_size=0.25)
    model.fit(trainset)
    predictions = model.test(testset)
    rmse_value = rmse(predictions)
    user_id = str(session.get("CustomerID"))
    top_n_recommendations = get_top_n_recommendations(predictions, n=2)
    data_list = []
    for arr in top_n_recommendations.values():
        data_list.append({'CourseName': arr[0][0]})
    return render_template("recommendation.html", data_list=data_list,user_id=user_id,rmse_value=rmse_value)


# Function to get top N recommendations for a user
def get_top_n_recommendations(predictions, n=2):
    top_n = {}
    for uid, iid, true_r, est, _ in predictions:
        if uid not in top_n:
            top_n[uid] = []
        top_n[uid].append((iid, est))

    # Sort the predictions for each user and get the top N
    for uid, user_ratings in top_n.items():
        user_ratings.sort(key=lambda x: x[1], reverse=True)
        top_n[uid] = user_ratings[:n]

    return top_n

if __name__ == '__main__':
    app.run()
