from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from create_blog_modal import BlogCreate, BlogOut
from user_models import UserCreate, UserLogin
from auth_utils import hash_password, verify_password, create_access_token, decode_token
from db_function import get_connection
from uuid import uuid4
from datetime import datetime
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username

@app.post("/signup")
def signup(user: UserCreate):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s;", (user.username,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = hash_password(user.password)
    cur.execute("""
        INSERT INTO users (id, username, password_hash)
        VALUES (%s, %s, %s);
    """, (str(uuid4()), user.username, hashed))
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "User created"}

#Login route
@app.post("/login")
def login(user: UserLogin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username = %s;", (user.username,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not verify_password(user.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/blogs", response_model=BlogOut)
def create_blog(blog: BlogCreate, username: str = Depends(get_current_user)):
    print(f"User {username} is creating a blog")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO blogs (id, title, content, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id, title, content, created_at, is_deleted;
    """, (str(uuid4()), blog.title, blog.content, datetime.utcnow()))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return {
        "id": result[0],
        "title": result[1],
        "content": result[2],
        "created_at": result[3].isoformat(),
        "is_deleted": result[4]
    }

@app.get("/blogs", response_model=list[BlogOut])
def get_blogs(page: int = 1, limit: int = 5):
    offset = (page - 1) * limit
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, content, created_at, is_deleted
        FROM blogs
        WHERE is_deleted = FALSE
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s;
    """, (limit, offset))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "created_at": row[3].isoformat(),
            "is_deleted": row[4]
        }
        for row in rows
    ]

@app.get("/blogs/{blog_id}", response_model=BlogOut)
def get_blog(blog_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, content, created_at, is_deleted
        FROM blogs
        WHERE id = %s;
    """, (blog_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "created_at": row[3].isoformat(),
        "is_deleted": row[4]
    }

@app.put("/blogs/{blog_id}", response_model=BlogOut)
def update_blog(blog_id: str, blog: BlogCreate):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE blogs
        SET title = %s, content = %s
        WHERE id = %s
        RETURNING id, title, content, created_at, is_deleted;
    """, (blog.title, blog.content, blog_id))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {
        "id": result[0],
        "title": result[1],
        "content": result[2],
        "created_at": result[3].isoformat(),
        "is_deleted": result[4]
    }

@app.patch("/blogs/{blog_id}/delete", response_model=BlogOut)
def soft_delete_blog(blog_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE blogs
        SET is_deleted = TRUE
        WHERE id = %s
        RETURNING id, title, content, created_at, is_deleted;
    """, (blog_id,))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {
        "id": result[0],
        "title": result[1],
        "content": result[2],
        "created_at": result[3].isoformat(),
        "is_deleted": result[4]
    }

@app.patch("/blogs/{blog_id}/restore", response_model=BlogOut)
def restore_blog(blog_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE blogs
        SET is_deleted = FALSE
        WHERE id = %s
        RETURNING id, title, content, created_at, is_deleted;
    """, (blog_id,))
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {
        "id": result[0],
        "title": result[1],
        "content": result[2],
        "created_at": result[3].isoformat(),
        "is_deleted": result[4]
    }

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
