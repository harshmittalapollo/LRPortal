import json

import pandas as pd

from auth import hash_password
from database import Base, SessionLocal, engine
from models import Permission, ReportRow, User


EXCEL_FILE = "LR Data.xlsx"
REPORT_SHEET = "LR Data"
USER_SHEET = "User Sheet"
NO_ACCESS_VALUES = {"", "nan", "none", "not view", "no view", "hide"}
VIEW_VALUES = {"only view", "view", "read"}
EDIT_VALUES = {"update", "edit"}
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "abcd@1234"


def clean_value(value):
    if pd.isna(value):
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def normalize_access(value):
    access = str(value).strip().lower()
    if access in EDIT_VALUES:
        return "edit"
    if access in VIEW_VALUES:
        return "view"
    if access in NO_ACCESS_VALUES:
        return "none"
    return "none"


def import_excel():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    users = pd.read_excel(EXCEL_FILE, sheet_name=USER_SHEET)
    report = pd.read_excel(EXCEL_FILE, sheet_name=REPORT_SHEET)

    db.query(Permission).delete()
    db.query(ReportRow).delete()

    user_columns = {"User", "User Name", "Password"}
    report_columns = [str(column).strip() for column in report.columns]

    for _, row in users.iterrows():
        username = clean_value(row.get("User Name")).strip()
        password = clean_value(row.get("Password")).strip()

        if not username or not password:
            continue

        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(username=username, role="User")
            db.add(user)

        user.password = hash_password(password)
        user.role = "User"

        for column in report_columns:
            if column in user_columns:
                continue

            access = normalize_access(row.get(column, ""))
            db.add(
                Permission(
                    username=username,
                    column_name=column,
                    access=access,
                )
            )

    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if not admin:
        admin = User(username=ADMIN_USERNAME)
        db.add(admin)

    admin.password = hash_password(ADMIN_PASSWORD)
    admin.role = "Admin"

    for column in report_columns:
        db.add(
            Permission(
                username=ADMIN_USERNAME,
                column_name=column,
                access="edit",
            )
        )

    for _, row in report.iterrows():
        row_data = {
            str(column).strip(): clean_value(row.get(column))
            for column in report.columns
        }
        db.add(ReportRow(row_data=json.dumps(row_data), updated_by="excel_import"))

    db.commit()
    db.close()


if __name__ == "__main__":
    import_excel()
    print("Import complete")
