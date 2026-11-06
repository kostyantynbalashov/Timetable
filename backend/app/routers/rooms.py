from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("", response_model=list[schemas.RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(models.Room).all()


@router.post("", response_model=schemas.RoomOut, status_code=201)
def create_room(body: schemas.RoomIn, db: Session = Depends(get_db)):
    room = models.Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/{room_id}", response_model=schemas.RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    return room


@router.put("/{room_id}", response_model=schemas.RoomOut)
def update_room(room_id: int, body: schemas.RoomIn, db: Session = Depends(get_db)):
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    for k, v in body.model_dump().items():
        setattr(room, k, v)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    db.delete(room)
    db.commit()
