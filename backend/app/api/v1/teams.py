from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.team import (
    OrgCreate, OrgRead, OrgMemberRead, OrgDetailRead,
    AddMemberRequest, ResourceShareCreate, ResourceShareRead,
)
from typing import List

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("/", response_model=OrgRead)
async def create_organization(
    data: OrgCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new organization. Current user becomes the owner."""
    org = models.Organization(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)

    # Add owner as admin member
    member = models.OrganizationMember(
        org_id=org.id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(member)
    await db.flush()

    return OrgRead(
        id=org.id,
        name=org.name,
        description=org.description,
        owner_id=org.owner_id,
        created_at=org.created_at,
        member_count=1,
    )


@router.get("/", response_model=List[OrgRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all organizations the current user belongs to."""
    # Get org IDs user is a member of
    member_query = select(models.OrganizationMember.org_id).where(
        models.OrganizationMember.user_id == current_user.id
    )
    result = await db.execute(
        select(models.Organization).where(
            models.Organization.id.in_(member_query)
        ).order_by(models.Organization.created_at.desc())
    )
    orgs = result.scalars().all()

    # Build response with member counts
    items = []
    for org in orgs:
        count_result = await db.execute(
            select(func.count()).select_from(models.OrganizationMember).where(
                models.OrganizationMember.org_id == org.id
            )
        )
        member_count = count_result.scalar() or 0
        items.append(OrgRead(
            id=org.id,
            name=org.name,
            description=org.description,
            owner_id=org.owner_id,
            created_at=org.created_at,
            member_count=member_count,
        ))
    return items


@router.get("/{org_id}", response_model=OrgDetailRead)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get organization details with members."""
    # Verify user is a member
    membership = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == current_user.id,
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get members with usernames
    members_result = await db.execute(
        select(models.OrganizationMember, models.User.username).join(
            models.User, models.OrganizationMember.user_id == models.User.id
        ).where(models.OrganizationMember.org_id == org_id)
    )
    members = []
    for member, username in members_result.all():
        members.append(OrgMemberRead(
            id=member.id,
            user_id=member.user_id,
            username=username,
            role=member.role,
            joined_at=member.joined_at,
        ))

    return OrgDetailRead(
        id=org.id,
        name=org.name,
        description=org.description,
        owner_id=org.owner_id,
        created_at=org.created_at,
        member_count=len(members),
        members=members,
    )


@router.post("/{org_id}/members", response_model=OrgMemberRead)
async def add_member(
    org_id: int,
    data: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a member to the organization (owner/admin only)."""
    # Check caller is admin or owner
    caller_member = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == current_user.id,
        )
    )
    caller = caller_member.scalar_one_or_none()
    if not caller or caller.role not in ("admin",):
        # Also check if owner
        org_result = await db.execute(
            select(models.Organization).where(models.Organization.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        if not org or org.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only admins or owner can add members")

    # Find user by username
    user_result = await db.execute(
        select(models.User).where(models.User.username == data.username)
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check not already a member
    existing = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    role = data.role if data.role in ("admin", "member", "viewer") else "member"
    member = models.OrganizationMember(
        org_id=org_id,
        user_id=target_user.id,
        role=role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    return OrgMemberRead(
        id=member.id,
        user_id=member.user_id,
        username=target_user.username,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(
    org_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a member from the organization."""
    # Check caller is admin/owner or removing self
    org_result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    is_owner = org.owner_id == current_user.id
    caller_member_result = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == current_user.id,
        )
    )
    caller_member = caller_member_result.scalar_one_or_none()
    is_admin = caller_member and caller_member.role == "admin"
    is_self = user_id == current_user.id

    if not (is_owner or is_admin or is_self):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Cannot remove owner
    if user_id == org.owner_id and not is_self:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")

    target_result = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == user_id,
        )
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    await db.delete(target)
    await db.flush()
    return {"detail": "Member removed"}


@router.post("/{org_id}/share", response_model=ResourceShareRead)
async def share_resource(
    org_id: int,
    data: ResourceShareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Share a resource with the organization."""
    # Verify user is a member
    membership = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == current_user.id,
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    if data.resource_type not in ("evaluation", "dataset", "model"):
        raise HTTPException(status_code=400, detail="Invalid resource type")

    # Check not already shared
    existing = await db.execute(
        select(models.ResourceShare).where(
            models.ResourceShare.org_id == org_id,
            models.ResourceShare.resource_type == data.resource_type,
            models.ResourceShare.resource_id == data.resource_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Resource already shared with this organization")

    share = models.ResourceShare(
        org_id=org_id,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        shared_by=current_user.id,
    )
    db.add(share)
    await db.flush()
    await db.refresh(share)
    return share


@router.get("/{org_id}/shared", response_model=List[ResourceShareRead])
async def list_shared_resources(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all resources shared with the organization."""
    # Verify user is a member
    membership = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == current_user.id,
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    result = await db.execute(
        select(models.ResourceShare).where(
            models.ResourceShare.org_id == org_id
        ).order_by(models.ResourceShare.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{org_id}/share/{share_id}")
async def unshare_resource(
    org_id: int,
    share_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a shared resource from the organization."""
    result = await db.execute(
        select(models.ResourceShare).where(
            models.ResourceShare.id == share_id,
            models.ResourceShare.org_id == org_id,
        )
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Shared resource not found")

    # Only the person who shared it, org admin, or owner can unshare
    org_result = await db.execute(
        select(models.Organization).where(models.Organization.id == org_id)
    )
    org = org_result.scalar_one_or_none()

    caller_member_result = await db.execute(
        select(models.OrganizationMember).where(
            models.OrganizationMember.org_id == org_id,
            models.OrganizationMember.user_id == current_user.id,
        )
    )
    caller_member = caller_member_result.scalar_one_or_none()

    is_owner = org and org.owner_id == current_user.id
    is_admin = caller_member and caller_member.role == "admin"
    is_sharer = share.shared_by == current_user.id

    if not (is_owner or is_admin or is_sharer):
        raise HTTPException(status_code=403, detail="Permission denied")

    await db.delete(share)
    await db.flush()
    return {"detail": "Resource unshared"}
