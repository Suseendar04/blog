from pydantic import BaseModel

class BlogCreate(BaseModel):
    title: str
    content: str

class BlogOut(BlogCreate):
    id: str
    created_at: str
    is_deleted: bool
