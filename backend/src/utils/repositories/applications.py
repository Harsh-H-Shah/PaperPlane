"""Application-attempt persistence, mixed into Database. Uses self.session()."""
from datetime import datetime

from src.core.application import Application
from src.utils.models import ApplicationModel


class ApplicationRepositoryMixin:
    def add_application(self, application: Application) -> str:
        app_id = application.id or f"app_{application.job_id}_{int(datetime.now().timestamp())}"
        application.id = app_id

        with self.session() as session:
            app_model = ApplicationModel(
                id=app_id,
                job_id=application.job_id,
                job_title=application.job_title,
                company=application.company,
                job_url=application.job_url,
                application_type=application.application_type,
                status=application.status,
                created_at=application.created_at,
                questions=[q.model_dump(mode='json') for q in application.questions],
                logs=[log.model_dump(mode='json') for log in application.logs],
            )
            session.add(app_model)

        return app_id

    def update_application(self, application: Application) -> None:
        with self.session() as session:
            app_model = session.query(ApplicationModel).filter(
                ApplicationModel.id == application.id
            ).first()

            if app_model:
                app_model.status = application.status
                app_model.started_at = application.started_at
                app_model.completed_at = application.completed_at
                app_model.current_step = application.current_step
                app_model.total_steps = application.total_steps
                app_model.questions = [q.model_dump(mode='json') for q in application.questions]
                app_model.logs = [log.model_dump(mode='json') for log in application.logs]
                app_model.error_message = application.error_message
                app_model.retry_count = application.retry_count
