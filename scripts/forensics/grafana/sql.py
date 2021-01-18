import mysql.connector

mydb = mysql.connector.connect(
  host="localhost",
  user="test",
  password="test",
  database="forensics"
)

mycursor = mydb.cursor()

def clear_node(table_name="node0"):
    sql_drop = "DROP TABLE IF EXISTS {}".format(table_name)
    sql_create = "CREATE TABLE {} (round INTEGER, B1 VARCHAR(100), B2 VARCHAR(100), B3 VARCHAR(100))".format(table_name)
    sql_insert = "INSERT INTO {} (round, B1, B2, B3) values (%s, %s, %s, %s)".format(table_name)
    val = (-1, "1", "2","3")
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mycursor.execute(sql_insert, val)
    mydb.commit()

def clear_images(img_name=1):
    sql_drop = "DROP TABLE IF EXISTS images"
    sql_create = "CREATE TABLE images (normal INTEGER)"
    sql_insert = "INSERT INTO images (normal) values (%s)"
    val = (img_name,)
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mycursor.execute(sql_insert, val)
    mydb.commit()

def clear_qcs():
    sql_drop = "DROP TABLE IF EXISTS qcs"
    sql_create = "CREATE TABLE qcs (round INTEGER, node0 VARCHAR(100), node1 VARCHAR(100), node2 VARCHAR(100), node3 VARCHAR(100))"
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mydb.commit()

def clear_qcs_twins():
    sql_drop = "DROP TABLE IF EXISTS qcs"
    sql_create = "CREATE TABLE qcs (round INTEGER, node0 VARCHAR(100), node1 VARCHAR(100), node2 VARCHAR(100), node3 VARCHAR(100), twin0 VARCHAR(100), twin1 VARCHAR(100))"
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mydb.commit()

def clear_culprits():
    sql_drop = "DROP TABLE IF EXISTS culprits"
    sql_create = "CREATE TABLE culprits (round INTEGER, culprits VARCHAR(50), commit1 INTEGER, commit2 INTEGER, prepare INTEGER)"
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mydb.commit()

def clear_conflict():
    sql_drop = "DROP TABLE IF EXISTS conflict"
    sql_create = "CREATE TABLE conflict (time TIMESTAMP, round INTEGER, diff INTEGER)"
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mydb.commit()   

def clear_text(nodes):
    sql_drop = "DROP TABLE IF EXISTS text"
    sql_create = "CREATE TABLE text (id VARCHAR(100) NOT NULL, is_culprit BOOL NOT NULL, content VARCHAR(1024), PRIMARY KEY (id))"
    # init the entry with default value
    sql_insert = "INSERT INTO text (id, is_culprit) values ('culprit', 0)"
    mycursor.execute(sql_drop)
    mycursor.execute(sql_create)
    mycursor.execute(sql_insert)
    for node in nodes:
        sql_insert = "INSERT INTO text (id, is_culprit) values ('{}', 0)".format(node)
        mycursor.execute(sql_insert)
    mydb.commit()

def insert_node(table_name, params):
    sql = "INSERT INTO {} (round, B1, B2, B3) VALUES (%s, %s, %s, %s)".format(table_name)
    val = params
    mycursor.execute(sql, val)
    mydb.commit()

def insert_qcs(params):
    sql = "INSERT INTO qcs (round, node0, node1, node2, node3) VALUES (%s, %s, %s, %s, %s)"
    val = params
    mycursor.execute(sql, val)
    mydb.commit()

def insert_culprits(params):
    sql = "INSERT INTO culprits (round, culprits, commit1, commit2, prepare) VALUES (%s, %s, %s, %s, %s)"
    val = params
    mycursor.execute(sql, val)
    mydb.commit()

def insert_conflict(params):
    sql = "INSERT INTO conflict (time, round, diff) VALUES (%s, %s, %s)"
    val = params
    mycursor.execute(sql, val)
    mydb.commit()

def insert_qcs_twins(params):
    sql = "INSERT INTO qcs (round, node0, node1, node2, node3, twin0, twin1) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    val = params
    mycursor.execute(sql, val)
    mydb.commit()

def delete_node(table_name, x=3):
    sql = "DELETE FROM {} WHERE round > -1 limit %s".format(table_name)
    val = (x,)
    mycursor.execute(sql, val)
    mydb.commit()

def delete_qcs(x=3):
    sql = "DELETE FROM qcs limit %s"
    val = (x,)
    mycursor.execute(sql, val)
    mydb.commit()

