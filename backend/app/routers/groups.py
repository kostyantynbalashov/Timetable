from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[schemas.GroupOut])
def list_groups(db: Session = Depends(get_db)):
    return db.query(models.Group).all()


@router.post("", response_model=schemas.GroupOut, status_code=201)
def create_group(body: schemas.GroupIn, db: Session = Depends(get_db)):
    group = models.Group(**body.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=schemas.GroupOut)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    return group


@router.put("/{group_id}", response_model=schemas.GroupOut)
def update_group(group_id: int, body: schemas.GroupIn, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    for k, v in body.model_dump().items():
        setattr(group, k, v)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    db.delete(group)
    db.commit()
