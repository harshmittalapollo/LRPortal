import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

class LoginRequest(BaseModel):
    username: str
    password: str

from auth import verify
from database import Base, SessionLocal, engine
from excel_import import import_excel
from jwt_auth import create_token
from models import AuditLog, Permission, ReportRow, User

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "abcd@1234"
DISPATCH_DATE_COLUMN = "Dispatch Dt."
LIMITED_ROW_CREATE_USERS = {"krishan"}
LIMITED_ROW_CREATE_COLUMNS = [
    "Customer",
    "Origin",
    "Destination",
    "Vehicle Type",
    "Vehicle No",
    "Vendor Freight",
    "Transport Name",
]
FRONTEND_BUILD_DIR = Path(__file__).resolve().parent.parent / "frontend" / "build"
FRONTEND_INDEX = FRONTEND_BUILD_DIR / "index.html"


class ReportCreate(BaseModel):
    username: str
    rowData: dict[str, object]


class UserCreate(BaseModel):
    adminUsername: str
    username: str
    password: str
    role: str = "User"
    permissions: dict[str, str] = Field(default_factory=dict)


class UserUpdate(BaseModel):
    adminUsername: str
    username: str
    password: str = ""
    role: str = "User"
    permissions: dict[str, str] = Field(default_factory=dict)

Base.metadata.create_all(bind=engine)

app=FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # temporary for local debugging
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db=SessionLocal()
    try:
        return db
    finally:
        pass


def ensure_excel_data():
    db=SessionLocal()
    try:
        if db.query(User).count()==0 or db.query(ReportRow).count()==0:
            db.close()
            import_excel()
    finally:
        try:
            db.close()
        except Exception:
            pass


ensure_excel_data()


def clean_input_value(value):
    if value is None:
        return ""
    return str(value)
    
def parse_row_data(row_data):
    try:
        if not row_data:
            return {}

        # if already dictionary
        if isinstance(row_data, dict):
            return row_data

        # convert JSON string to dict
        data = json.loads(row_data)

        if isinstance(data, dict):
            return data

        return {}

    except Exception:
        return {}

def get_report_columns(db):
    columns=[]
    seen=set()

    for row in db.query(ReportRow).order_by(ReportRow.id).all():
        try:
            data=parse_row_data(row.row_data)
        except Exception:
            data={}

        for column in data.keys():
            if column not in seen:
                seen.add(column)
                columns.append(column)

    if not columns:
        for permission in db.query(Permission).order_by(Permission.id).all():
            if permission.column_name not in seen:
                seen.add(permission.column_name)
                columns.append(permission.column_name)

    return columns


def ensure_admin_user():
    from auth import hash_password

    db=SessionLocal()
    try:
        admin=db.query(User).filter(User.username==ADMIN_USERNAME).first()
        if not admin:
            admin=User(username=ADMIN_USERNAME)
            db.add(admin)

        admin.password=hash_password(ADMIN_PASSWORD)
        admin.role="Admin"

        existing_permissions={
            permission.column_name
            for permission in db.query(Permission).filter(
                Permission.username==ADMIN_USERNAME
            ).all()
        }

        for column in get_report_columns(db):
            if column not in existing_permissions:
                db.add(
                    Permission(
                        username=ADMIN_USERNAME,
                        column_name=column,
                        access="edit"
                    )
                )

        db.commit()
    finally:
        db.close()


def user_is_admin(db, username):
    user=db.query(User).filter(User.username==username).first()
    return bool(user and user.role=="Admin")


def clean_username(value):
    return str(value or "").strip()


def user_can_add_report_row(db, username):
    normalized=clean_username(username).lower()
    return user_is_admin(db, username) or normalized in LIMITED_ROW_CREATE_USERS


def get_addable_columns(db, username):
    if user_is_admin(db, username):
        return get_report_columns(db)

    # For limited users (like Krishan) allow creating rows with the
    # predefined limited columns even if they don't exist yet so they
    # can add new fields when creating an entry.
    if clean_username(username).lower() in LIMITED_ROW_CREATE_USERS:
        return LIMITED_ROW_CREATE_COLUMNS

    return []


def require_admin(db, username):
    if not user_is_admin(db, username):
        return {"error":"Only admin can manage users"}
    return None


def normalize_permission_access(value):
    access=str(value or "none").strip().lower()
    if access in {"edit", "view", "none"}:
        return access
    if access in {"hide", "hidden", "no access"}:
        return "none"
    return "none"


def permission_map_for_user(db, username, columns):
    permissions=db.query(Permission).filter(Permission.username==username).all()
    access_by_column={
        permission.column_name: normalize_permission_access(permission.access)
        for permission in permissions
    }
    return {
        column: access_by_column.get(column, "none")
        for column in columns
    }


def serialize_user(db, user, columns):
    if user.role=="Admin":
        permissions={column:"edit" for column in columns}
    else:
        permissions=permission_map_for_user(db, user.username, columns)

    return {
        "id":user.id,
        "username":user.username,
        "role":user.role,
        "permissions":permissions
    }


def save_user_permissions(db, username, permissions):
    columns=get_report_columns(db)
    db.query(Permission).filter(Permission.username==username).delete()

    for column in columns:
        db.add(
            Permission(
                username=username,
                column_name=column,
                access=normalize_permission_access(permissions.get(column, "none"))
            )
        )


def parse_dispatch_month(value):
    if value is None:
        return ""

    text=str(value).strip()
    if not text:
        return ""

    for parser in (
        lambda item: datetime.fromisoformat(item.replace("Z", "+00:00")),
        lambda item: datetime.strptime(item[:10], "%Y-%m-%d"),
        lambda item: datetime.strptime(item[:10], "%d-%m-%Y"),
        lambda item: datetime.strptime(item[:10], "%d/%m/%Y"),
    ):
        try:
            return parser(text).strftime("%Y-%m")
        except Exception:
            pass

    return ""


ensure_admin_user()


@app.get("/")
def home():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return {"status":"running"}


@app.post("/login")
def login(
    request: LoginRequest | None = Body(default=None),
    username: str | None = Query(default=None),
    password: str | None = Query(default=None),
):
    if request is not None:
        username = request.username
        password = request.password

    if not username or not password:
        raise HTTPException(status_code=422, detail="Username and password are required")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()

        if not user:
            return {"error": "User not found"}

        if not verify(password, user.password):
            return {"error": "Invalid password"}

        return {
            "token": create_token(username),
            "username": username,
            "role": user.role,
        }
    finally:
        db.close()


@app.post("/import-excel")
def import_from_excel():
    import_excel()
    return {"message":"Import complete"}


@app.get("/admin/users")
def list_users(adminUsername:str):
    db=SessionLocal()
    try:
        denied=require_admin(db, adminUsername)
        if denied:
            return denied

        columns=get_report_columns(db)
        return {
            "columns":columns,
            "users":[
                serialize_user(db, user, columns)
                for user in db.query(User).order_by(User.username).all()
            ]
        }
    finally:
        db.close()


@app.post("/admin/users")
def create_user(payload:UserCreate):
    from auth import hash_password

    db=SessionLocal()
    try:
        denied=require_admin(db, payload.adminUsername)
        if denied:
            return denied

        username=clean_username(payload.username)
        password=str(payload.password or "")
        role="Admin" if payload.role=="Admin" else "User"

        if not username:
            return {"error":"Username is required"}
        if not password:
            return {"error":"Password is required"}
        if db.query(User).filter(User.username==username).first():
            return {"error":"Username already exists"}

        user=User(
            username=username,
            password=hash_password(password),
            role=role
        )
        db.add(user)

        if role=="Admin":
            for column in get_report_columns(db):
                db.add(Permission(username=username, column_name=column, access="edit"))
        else:
            save_user_permissions(db, username, payload.permissions)

        db.commit()
        db.refresh(user)

        return {
            "message":"created",
            "user":serialize_user(db, user, get_report_columns(db))
        }
    finally:
        db.close()


@app.put("/admin/users/{user_id}")
def update_user(user_id:int, payload:UserUpdate):
    from auth import hash_password

    db=SessionLocal()
    try:
        denied=require_admin(db, payload.adminUsername)
        if denied:
            return denied

        user=db.query(User).filter(User.id==user_id).first()
        if not user:
            return {"error":"User not found"}

        username=clean_username(payload.username)
        if not username:
            return {"error":"Username is required"}

        duplicate=db.query(User).filter(
            User.username==username,
            User.id!=user_id
        ).first()
        if duplicate:
            return {"error":"Username already exists"}

        old_username=user.username
        role="Admin" if payload.role=="Admin" else "User"
        user.username=username
        user.role=role
        if payload.password:
            user.password=hash_password(payload.password)

        if old_username!=username:
            db.query(Permission).filter(Permission.username==old_username).update(
                {Permission.username:username},
                synchronize_session=False
            )

        if role=="Admin":
            existing_permissions={
                permission.column_name
                for permission in db.query(Permission).filter(
                    Permission.username==username
                ).all()
            }
            for column in get_report_columns(db):
                if column not in existing_permissions:
                    db.add(Permission(username=username, column_name=column, access="edit"))
        else:
            save_user_permissions(db, username, payload.permissions)

        db.commit()
        db.refresh(user)

        return {
            "message":"updated",
            "user":serialize_user(db, user, get_report_columns(db))
        }
    finally:
        db.close()


@app.delete("/admin/users/{user_id}")
def delete_user(user_id:int, adminUsername:str):
    db=SessionLocal()
    try:
        denied=require_admin(db, adminUsername)
        if denied:
            return denied

        user=db.query(User).filter(User.id==user_id).first()
        if not user:
            return {"error":"User not found"}
        if user.username==adminUsername:
            return {"error":"You cannot delete your own admin user"}

        db.query(Permission).filter(Permission.username==user.username).delete()
        db.delete(user)
        db.commit()

        return {"message":"deleted"}
    finally:
        db.close()


@app.get("/report")
def report(username:str, month:str=""):
    db=SessionLocal()
    try:
        all_columns=get_report_columns(db)
        is_admin=user_is_admin(db, username)

        if is_admin:
            access_by_column={column:"edit" for column in all_columns}
        else:
            permissions=db.query(Permission).filter(
                Permission.username==username
            ).all()

            access_by_column={
                permission.column_name: normalize_permission_access(permission.access)
                for permission in permissions
            }

        visible_columns=[]
        for column in all_columns:
            access=normalize_permission_access(access_by_column.get(column, "none"))
            if access in {"view","edit"}:
                visible_columns.append(
                    {
                        "field":column,
                        "headerName":column,
                        "access":access
                    }
                )

        editable_columns=[
            column["field"]
            for column in visible_columns
            if column["access"]=="edit"
        ]
        addable_columns=get_addable_columns(db, username)

        rows=[]
        available_months=set()
        for row in db.query(ReportRow).order_by(ReportRow.id).all():
            data=parse_row_data(row.row_data)
            dispatch_month=parse_dispatch_month(data.get(DISPATCH_DATE_COLUMN, ""))
            if dispatch_month:
                available_months.add(dispatch_month)

            if month and dispatch_month!=month:
                continue

            filtered={
                column["field"]: data.get(column["field"],"")
                for column in visible_columns
            }
            filtered["id"]=row.id
            filtered["version"]=row.version
            rows.append(filtered)

        return {
            "columns":visible_columns,
            "editableColumns":editable_columns,
            "canAddRows":bool(addable_columns),
            "addableColumns":[
                {
                    "field":column,
                    "headerName":column
                }
                for column in addable_columns
            ],
            "rows":rows,
            "months":sorted(available_months, reverse=True),
            "selectedMonth":month
        }
    finally:
        db.close()


@app.put("/report/{row_id}")
def update_report(
    row_id: int,
    field: str = None,
    value: str = None,
    version: int = None,
    username: str = None,
    payload: dict = Body(None),
):
    # Accept either query params or JSON body payload
    if payload and isinstance(payload, dict):
        if field is None:
            field = payload.get("field")
        if value is None and "value" in payload:
            value = payload.get("value")
        if version is None:
            version = payload.get("version")
        if username is None:
            username = payload.get("username")

    db = SessionLocal()
    try:
        username = clean_username(username)
        if not username or not field:
            raise HTTPException(status_code=400, detail="Username and field are required")

        try:
            version = int(version)
        except (TypeError, ValueError):
            version = None

        permission=db.query(Permission).filter(
            Permission.username==username,
            Permission.column_name==field
        ).first()

        # normalize access (stores like 'edit'/'view'/'none')
        access = normalize_permission_access(permission.access) if permission else "none"
        if access != "edit" and not user_is_admin(db, username):
            raise HTTPException(status_code=403, detail="You do not have edit access for this column")

        row=db.query(ReportRow).filter(ReportRow.id==row_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Row not found")

        if version is None or row.version!=version:
            raise HTTPException(status_code=409, detail="This row was updated by another user. Refresh the report.")

        data=parse_row_data(row.row_data)
        old=str(data.get(field,""))
        if not isinstance(data, dict):data = {}
        data[field] = clean_input_value(value)

        row.row_data=json.dumps(data)
        row.version+=1
        row.updated_by=username
        row.updated_at=datetime.utcnow()

        db.add(
            AuditLog(
                lr_no=str(data.get("LR NO",row_id)),
                column_name=field,
                old_value=old,
                new_value=clean_input_value(value),
                updated_by=username
            )
        )

        db.commit()

        return {
            "message":"updated",
            "row":{
                "id":row.id,
                field:clean_input_value(value),
                "version":row.version
            }
        }
    finally:
        db.close()


@app.post("/report")
def create_report(payload:ReportCreate):
    db=SessionLocal()
    try:
        addable_columns=get_addable_columns(db, payload.username)
        if not addable_columns:
            return {"error":"You do not have access to add a new entry"}

        columns=get_report_columns(db)
        # include any new columns provided in payload.rowData
        original_columns = get_report_columns(db)
        for col in (payload.rowData or {}).keys():
            if col not in columns:
                columns.append(col)

        # determine which columns are newly introduced by this payload
        new_columns = [c for c in columns if c not in original_columns]

        # Ensure Permission rows exist for new columns. Grant 'edit' to
        # admin and to the creating user; others get 'none' by default.
        if new_columns:
            users = db.query(User).all()
            for new_col in new_columns:
                for u in users:
                    existing = db.query(Permission).filter(
                        Permission.username == u.username,
                        Permission.column_name == new_col,
                    ).first()
                    if existing:
                        continue
                    access = "none"
                    if u.username == ADMIN_USERNAME:
                        access = "edit"
                    if u.username == payload.username:
                        access = "edit"
                    db.add(
                        Permission(
                            username=u.username,
                            column_name=new_col,
                            access=access,
                        )
                    )
            db.commit()

        # Build row data for all columns (including newly provided ones)
        row_data={
            column: clean_input_value(payload.rowData.get(column, ""))
            for column in columns
        }

        if not user_is_admin(db, payload.username):
            # Non-admin users can only set values for addable columns
            row_data={
                column: clean_input_value(payload.rowData.get(column, ""))
                if column in addable_columns
                else ""
                for column in columns
            }

        row=ReportRow(
            row_data=json.dumps(row_data if isinstance(row_data, dict) else {}),
            updated_by=payload.username
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        db.add(
            AuditLog(
                lr_no=str(row_data.get("LR NO", row.id)),
                column_name="ROW",
                old_value="",
                new_value="created",
                updated_by=payload.username
            )
        )
        db.commit()

        return {
            "message":"created",
            "row":{
                **row_data,
                "id":row.id,
                "version":row.version
            }
        }
    finally:
        db.close()


@app.get("/export")
def export_data(username: str, month: str = ""):
    db = SessionLocal()
    try:
        all_columns = get_report_columns(db)
        is_admin = user_is_admin(db, username)

        if is_admin:
            access_by_column = {column: "edit" for column in all_columns}
        else:
            permissions = db.query(Permission).filter(
                Permission.username == username
            ).all()
            access_by_column = {
                permission.column_name: permission.access
                for permission in permissions
            }

        visible_columns = []
        for column in all_columns:
            access = access_by_column.get(column, "none")
            if access in {"view", "edit"}:
                visible_columns.append(column)

        rows = []
        for row in db.query(ReportRow).order_by(ReportRow.id).all():
            data = json.loads(row.row_data)
            dispatch_month = parse_dispatch_month(data.get(DISPATCH_DATE_COLUMN, ""))

            if month and dispatch_month != month:
                continue

            filtered = {
                column: data.get(column, "")
                for column in visible_columns
            }
            rows.append(filtered)

        output = io.StringIO()
        if visible_columns:
            writer = csv.DictWriter(output, fieldnames=visible_columns)
            writer.writeheader()
            writer.writerows(rows)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=report_{username}_{month if month else 'all'}.csv"}
        )
    finally:
        db.close()


@app.get("/audit/{lr_no}")
def audit(lr_no:str):
    db=SessionLocal()
    try:
        logs=db.query(AuditLog).filter(AuditLog.lr_no==lr_no).all()
        return logs
    finally:
        db.close()


@app.get("/{full_path:path}")
def serve_frontend(full_path:str):
    requested_path=(FRONTEND_BUILD_DIR / full_path).resolve()
    build_root=FRONTEND_BUILD_DIR.resolve()

    if (
        FRONTEND_BUILD_DIR.exists()
        and str(requested_path).startswith(str(build_root))
        and requested_path.is_file()
    ):
        return FileResponse(requested_path)

    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)

    return {"error":"Frontend build not found"}
