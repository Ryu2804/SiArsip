from pydantic import BaseModel

class CreateUser(BaseModel):
    username: str
    email: str
    password: str

class UpdateUser(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str | None = None
