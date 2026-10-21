import re

from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError

from app.api.routes.auth import get_current_user
from app.db import mongo
from app.models.schemas import Brand, BrandCreate

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.post("", response_model=Brand, status_code=status.HTTP_201_CREATED)
async def create_brand(payload: BrandCreate, user: dict = Depends(get_current_user)):
	user_id = str(user["_id"])
	collection = mongo.get_db().brands
	normalized_name = payload.name.casefold()
	existing = await collection.find_one({
		"user_id": user_id,
		"$or": [
			{"normalized_name": normalized_name},
			{"name": {"$regex": rf"^\s*{re.escape(payload.name)}\s*$", "$options": "i"}},
		],
	})
	if existing:
		raise HTTPException(status_code=409, detail="A brand with this name already exists")

	brand = Brand(user_id=user_id, **payload.model_dump())
	document = brand.to_mongo()
	document["normalized_name"] = normalized_name
	try:
		result = await collection.insert_one(document)
	except DuplicateKeyError:
		raise HTTPException(status_code=409, detail="A brand with this name already exists")
	return brand.model_copy(update={"id": str(result.inserted_id)})


@router.get("", response_model=list[Brand])
async def list_brands(user: dict = Depends(get_current_user)):
	cursor = mongo.get_db().brands.find({"user_id": str(user["_id"])}).sort("created_at", -1)
	documents = await cursor.to_list(length=100)
	return [Brand.model_validate(document) for document in documents]


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(brand_id: str, user: dict = Depends(get_current_user)):
	try:
		object_id = mongo.oid(brand_id)
	except InvalidId:
		raise HTTPException(status_code=404, detail="Brand not found")
	result = await mongo.get_db().brands.delete_one({
		"_id": object_id,
		"user_id": str(user["_id"]),
	})
	if result.deleted_count == 0:
		raise HTTPException(status_code=404, detail="Brand not found")
	return Response(status_code=status.HTTP_204_NO_CONTENT)
