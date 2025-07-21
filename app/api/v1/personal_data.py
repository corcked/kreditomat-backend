from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.jwt import get_current_user
from app.models.user import User
from app.models.personal_data import PersonalData
from app.schemas.personal_data import (
    PersonalDataCreate, PersonalDataUpdate, PersonalDataResponse,
    PersonalDataSummary, DataCompletionCheck
)

router = APIRouter()


def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def check_data_completion(data: PersonalData) -> tuple[int, list[str]]:
    """
    Check personal data completion
    
    Returns:
        (completion_percentage, missing_fields)
    """
    required_fields = [
        'first_name', 'last_name', 'birth_date', 'gender', 'marital_status',
        'passport_series', 'passport_number', 'passport_issued_by', 'passport_issue_date',
        'inn', 'region', 'city', 'address', 'education', 'employment_type',
        'monthly_income', 'income_source', 'living_arrangement'
    ]
    
    optional_fields = [
        'middle_name', 'email', 'workplace', 'position', 'living_address'
    ]
    
    missing_required = []
    missing_optional = []
    
    for field in required_fields:
        value = getattr(data, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_required.append(field)
    
    for field in optional_fields:
        value = getattr(data, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_optional.append(field)
    
    # Calculate percentage based on required fields only
    completion = int((len(required_fields) - len(missing_required)) / len(required_fields) * 100)
    
    return completion, missing_required


@router.get("/", response_model=Optional[PersonalDataResponse])
async def get_personal_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Optional[PersonalDataResponse]:
    """
    Get current user's personal data
    
    Requires authentication
    """
    result = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    personal_data = result.scalars().first()
    
    if not personal_data:
        return None
    
    return PersonalDataResponse.model_validate(personal_data)


@router.post("/", response_model=PersonalDataResponse)
async def create_personal_data(
    data: PersonalDataCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PersonalDataResponse:
    """
    Create personal data for current user
    
    Requires authentication
    """
    # Check if personal data already exists
    existing = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Personal data already exists. Use PUT to update."
        )
    
    # Create personal data
    personal_data = PersonalData(
        user_id=current_user.id,
        **data.model_dump()
    )
    
    db.add(personal_data)
    await db.commit()
    await db.refresh(personal_data)
    
    return PersonalDataResponse.model_validate(personal_data)


@router.put("/", response_model=PersonalDataResponse)
async def update_personal_data(
    data: PersonalDataUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PersonalDataResponse:
    """
    Update personal data for current user
    
    Requires authentication
    """
    # Get existing personal data
    result = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    personal_data = result.scalars().first()
    
    if not personal_data:
        raise HTTPException(
            status_code=404,
            detail="Personal data not found. Use POST to create."
        )
    
    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(personal_data, field, value)
    
    await db.commit()
    await db.refresh(personal_data)
    
    return PersonalDataResponse.model_validate(personal_data)


@router.get("/summary", response_model=PersonalDataSummary)
async def get_personal_data_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PersonalDataSummary:
    """
    Get summary of personal data
    
    Requires authentication
    """
    result = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    personal_data = result.scalars().first()
    
    if not personal_data:
        raise HTTPException(
            status_code=404,
            detail="Personal data not found"
        )
    
    # Calculate completion
    completion, missing_fields = check_data_completion(personal_data)
    
    # Build full name
    full_name_parts = [personal_data.last_name, personal_data.first_name]
    if personal_data.middle_name:
        full_name_parts.append(personal_data.middle_name)
    full_name = " ".join(full_name_parts)
    
    return PersonalDataSummary(
        full_name=full_name,
        age=calculate_age(personal_data.birth_date),
        gender=personal_data.gender,
        marital_status=personal_data.marital_status,
        employment_type=personal_data.employment_type,
        monthly_income=personal_data.monthly_income,
        has_complete_data=len(missing_fields) == 0,
        completion_percentage=completion,
        missing_fields=missing_fields
    )


@router.get("/completion", response_model=DataCompletionCheck)
async def check_personal_data_completion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DataCompletionCheck:
    """
    Check personal data completion status
    
    Requires authentication
    """
    result = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    personal_data = result.scalars().first()
    
    required_fields = [
        'first_name', 'last_name', 'birth_date', 'gender', 'marital_status',
        'passport_series', 'passport_number', 'passport_issued_by', 'passport_issue_date',
        'inn', 'region', 'city', 'address', 'education', 'employment_type',
        'monthly_income', 'income_source', 'living_arrangement'
    ]
    
    optional_fields = [
        'middle_name', 'email', 'workplace', 'position', 'living_address',
        'children_count', 'additional_income', 'monthly_expenses',
        'existing_loans_count', 'existing_loans_monthly_payment'
    ]
    
    if not personal_data:
        return DataCompletionCheck(
            is_complete=False,
            completion_percentage=0,
            required_fields=required_fields,
            missing_fields=required_fields,
            optional_fields=optional_fields,
            missing_optional=optional_fields
        )
    
    missing_required = []
    missing_optional = []
    
    for field in required_fields:
        value = getattr(personal_data, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_required.append(field)
    
    for field in optional_fields:
        value = getattr(personal_data, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_optional.append(field)
    
    completion = int((len(required_fields) - len(missing_required)) / len(required_fields) * 100)
    
    return DataCompletionCheck(
        is_complete=len(missing_required) == 0,
        completion_percentage=completion,
        required_fields=required_fields,
        missing_fields=missing_required,
        optional_fields=optional_fields,
        missing_optional=missing_optional
    )


@router.post("/validate", response_model=dict)
async def validate_personal_data(
    data: PersonalDataCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Validate personal data without saving
    
    Requires authentication
    """
    errors = []
    warnings = []
    
    # Age validation
    age = calculate_age(data.birth_date)
    if age < 21:
        warnings.append("Возраст менее 21 года может снизить шансы на одобрение")
    elif age > 65:
        warnings.append("Возраст более 65 лет может ограничить доступные предложения")
    
    # Income validation
    if data.monthly_income < 500000:  # 500k sum
        warnings.append("Низкий уровень дохода может ограничить сумму займа")
    
    # Debt burden check
    if data.existing_loans_monthly_payment > data.monthly_income * 0.4:
        warnings.append("Высокая долговая нагрузка может привести к отказу")
    
    # Employment validation
    if data.employment_type == "unemployed":
        errors.append("Необходимо иметь источник дохода для получения займа")
    elif data.employment_duration_months < 3:
        warnings.append("Стаж работы менее 3 месяцев может снизить шансы на одобрение")
    
    # Check passport issue date
    passport_age_years = (date.today() - data.passport_issue_date).days / 365
    if passport_age_years > 10:
        warnings.append("Паспорт выдан более 10 лет назад, возможно требуется замена")
    
    # Check if living address is provided when needed
    if not data.living_address_same_as_registration and not data.living_address:
        errors.append("Необходимо указать фактический адрес проживания")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@router.get("/export", response_model=dict)
async def export_personal_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Export personal data in JSON format (GDPR compliance)
    
    Requires authentication
    """
    result = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    personal_data = result.scalars().first()
    
    if not personal_data:
        raise HTTPException(
            status_code=404,
            detail="Personal data not found"
        )
    
    # Convert to dict and remove sensitive internal fields
    data_dict = PersonalDataResponse.model_validate(personal_data).model_dump()
    
    # Add user info
    data_dict["user_info"] = {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat()
    }
    
    return {
        "exported_at": datetime.now().isoformat(),
        "data": data_dict
    }