import sqlite3

default_db = 'C:\ProgramData\GOG.com\Galaxy\storage\galaxy-2.0.db'


def open_db():
    conn = None
    try:
        conn = sqlite3.connect(default_db)
    except Error as e:
        print(e)

    return conn


def import_master(conn=open_db()):
    cur = conn.cursor()
    cur.execute("""SELECT GamePieces.releaseKey, GamePieces.gamePieceTypeId, GamePieces.value
    FROM GameLinks
	JOIN GamePieces ON GameLinks.releaseKey = GamePieces.releaseKey""")
    return cur.fetchall()


def import_tag(conn=open_db()):
    cur = conn.cursor()
    cur.execute("""SELECT releaseKey, tag FROM UserReleaseTags""")
    return cur.fetchall()


def import_hidden(conn=open_db()):
    cur = conn.cursor()
    cur.execute("""SELECT releaseKey, isDlc, isVisibleInLibrary FROM ReleaseProperties""")
    return cur.fetchall()


def import_user_hidden(conn=open_db()):
    cur = conn.cursor()
    cur.execute("""SELECT releaseKey, isHidden FROM UserReleaseProperties""")
    return cur.fetchall()
