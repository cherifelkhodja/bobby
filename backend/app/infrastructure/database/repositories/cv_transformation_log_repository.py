"""CV Transformation Log repository implementation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import CvTransformationLog
from app.infrastructure.database.models import CvTransformationLogModel, UserModel


class CvTransformationLogRepository:
    """CV Transformation Log repository implementation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, log: CvTransformationLog) -> CvTransformationLog:
        """Save transformation log."""
        model = CvTransformationLogModel(
            id=log.id,
            user_id=log.user_id,
            template_id=log.template_id,
            template_name=log.template_name,
            original_filename=log.original_filename,
            success=log.success,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_entity(model)

    async def count_by_user(self, user_id: UUID, success_only: bool = True) -> int:
        """Count transformations by user."""
        query = select(func.count(CvTransformationLogModel.id)).where(
            CvTransformationLogModel.user_id == user_id
        )
        if success_only:
            query = query.where(CvTransformationLogModel.success == True)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_stats_by_user(self) -> list[dict]:
        """Get transformation stats grouped by user.

        Returns a list of dicts with user_id, user_email, user_name, and count.
        """
        result = await self.session.execute(
            select(
                CvTransformationLogModel.user_id,
                UserModel.email,
                UserModel.first_name,
                UserModel.last_name,
                func.count(CvTransformationLogModel.id).label("count"),
            )
            .join(UserModel, CvTransformationLogModel.user_id == UserModel.id)
            .where(CvTransformationLogModel.success == True)
            .group_by(
                CvTransformationLogModel.user_id,
                UserModel.email,
                UserModel.first_name,
                UserModel.last_name,
            )
            .order_by(func.count(CvTransformationLogModel.id).desc())
        )

        return [
            {
                "user_id": str(row.user_id),
                "user_email": row.email,
                "user_name": f"{row.first_name} {row.last_name}",
                "count": row.count,
            }
            for row in result.all()
        ]

    async def get_total_count(self, success_only: bool = True) -> int:
        """Get total transformation count."""
        query = select(func.count(CvTransformationLogModel.id))
        if success_only:
            query = query.where(CvTransformationLogModel.success == True)
        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_entity(self, model: CvTransformationLogModel) -> CvTransformationLog:
        """Convert model to entity."""
        return CvTransformationLog(
            id=model.id,
            user_id=model.user_id,
            template_id=model.template_id,
            template_name=model.template_name,
            original_filename=model.original_filename,
            success=model.success,
            error_message=model.error_message,
            created_at=model.created_at,
        )
