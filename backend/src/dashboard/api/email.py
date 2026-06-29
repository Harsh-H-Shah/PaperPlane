"""Cold-email subsystem endpoints: contacts, emails, templates, campaigns, stats."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from src.utils.database import get_db
from src.utils.logger import logger
from src.utils import paths
from src.dashboard.dependencies import require_admin
from src.dashboard.schemas import (
    ContactCreate,
    ContactUpdate,
    EmailCreate,
    EmailUpdate,
    RenderEmail,
    CampaignCreate,
)

router = APIRouter()


# ============ Contacts ============

@router.get("/api/contacts")
async def list_contacts(
    company: Optional[str] = None,
    search: Optional[str] = None,
    persona: Optional[str] = None,
    job_id: Optional[str] = None,
    limit: int = 100
):
    """Get all contacts with optional search and filters"""
    db = get_db()

    if search or job_id or persona:
        contacts = db.search_contacts(query=search, job_id=job_id, persona=persona, limit=limit)
    elif company:
        contacts = db.get_contacts_for_company(company, limit)
    else:
        contacts = db.get_all_contacts(limit)

    return {
        "total": len(contacts),
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "title": c.title,
                "company": c.company,
                "linkedin_url": c.linkedin_url,
                "persona": c.persona.value if hasattr(c.persona, 'value') else c.persona,
                "source": c.source.value if hasattr(c.source, 'value') else c.source,
                "job_id": c.job_id,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contacts
        ]
    }


@router.post("/api/contacts", dependencies=[Depends(require_admin)])
async def create_contact(contact_in: ContactCreate):
    """Add a new contact manually"""
    from src.core.cold_email_models import Contact, ContactPersona, ContactSource

    db = get_db()

    contact = Contact(
        name=contact_in.name,
        email=contact_in.email,
        title=contact_in.title or "",
        company=contact_in.company,
        linkedin_url=contact_in.linkedin_url,
        persona=ContactPersona(contact_in.persona) if contact_in.persona else ContactPersona.UNKNOWN,
        source=ContactSource.MANUAL,
        job_id=contact_in.job_id,
        notes=contact_in.notes,
    )

    contact_id = db.add_contact(contact)
    return {"id": contact_id, "success": True}


@router.patch("/api/contacts/{contact_id}", dependencies=[Depends(require_admin)])
async def update_contact(contact_id: str, update: ContactUpdate):
    """Update a contact"""
    db = get_db()
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = db.update_contact_fields(contact_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"success": True}


@router.delete("/api/contacts/{contact_id}", dependencies=[Depends(require_admin)])
async def delete_contact(contact_id: str):
    """Delete a contact"""
    db = get_db()
    success = db.delete_contact(contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"success": True}


@router.post("/api/contacts/scrape", dependencies=[Depends(require_admin)])
async def scrape_contacts(
    company: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    limit: int = Query(10),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Scrape contacts from Apollo for a company or job"""
    if not company and not job_id:
        raise HTTPException(status_code=400, detail="Either company or job_id must be provided")

    async def run_scrape():
        try:
            from src.scrapers.apollo_scraper import ApolloScraper

            db = get_db()
            target_company = company

            # If job_id provided, get company from job
            if job_id and not target_company:
                job = db.get_job(job_id)
                if not job:
                    logger.error(f"   ❌ Job {job_id} not found")
                    return
                target_company = job.company

            if not target_company:
                logger.error("   ❌ No company found to scrape")
                return

            scraper = ApolloScraper()
            contacts = await scraper.search_contacts(company=target_company, limit=limit)

            # Link contacts to job if job_id provided
            if job_id:
                for contact in contacts:
                    contact.job_id = job_id

            count = db.add_contacts_bulk(contacts)
            logger.info(f"   ✅ Scraped {count} contacts for {target_company}" + (f" (linked to job {job_id})" if job_id else ""))
        except Exception as e:
            logger.error(f"   ❌ Contact scrape error: {e}")

    background_tasks.add_task(run_scrape)
    return {"status": "started", "message": f"Scraping contacts for {company or 'job'}"}


# ============ Emails ============

@router.get("/api/emails")
async def list_emails(
    status: Optional[str] = None,
    search: Optional[str] = None,
    job_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    limit: int = 100
):
    """Get all cold emails with enriched contact info"""
    from src.core.cold_email_models import EmailStatus as ES

    db = get_db()

    if search or job_id or contact_id:
        emails = db.search_cold_emails(query=search, status=status, job_id=job_id, contact_id=contact_id, limit=limit)
    elif status:
        emails = db.get_cold_emails_by_status(ES(status), limit)
    else:
        emails = db.get_all_cold_emails(limit)

    # Enrich with contact info
    contact_cache: dict = {}
    enriched = []
    for e in emails:
        if e.contact_id and e.contact_id not in contact_cache:
            contact_cache[e.contact_id] = db.get_contact(e.contact_id)
        contact = contact_cache.get(e.contact_id)
        enriched.append({
            "id": e.id,
            "contact_id": e.contact_id,
            "contact_name": contact.name if contact else "Unknown",
            "contact_email": contact.email if contact else "",
            "contact_company": contact.company if contact else "",
            "job_id": e.job_id,
            "template_id": e.template_id,
            "subject": e.subject,
            "body": e.body,
            "status": e.status.value if hasattr(e.status, 'value') else e.status,
            "scheduled_at": e.scheduled_at.isoformat() if e.scheduled_at else None,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "followup_number": e.followup_number,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "error_message": e.error_message,
        })

    return {"total": len(enriched), "emails": enriched}


@router.post("/api/emails", dependencies=[Depends(require_admin)])
async def create_email(email_in: EmailCreate):
    """Create a new cold email"""
    from src.core.cold_email_models import ColdEmail, EmailStatus

    db = get_db()

    email = ColdEmail(
        contact_id=email_in.contact_id,
        job_id=email_in.job_id,
        template_id=email_in.template_id,
        subject=email_in.subject,
        body=email_in.body,
        status=EmailStatus.DRAFT,
    )

    email_id = db.add_cold_email(email)
    return {"id": email_id, "success": True}


@router.post("/api/emails/render", dependencies=[Depends(require_admin)])
async def render_email_preview(data: RenderEmail):
    """Render an email from template for preview (without saving)"""
    try:
        db = get_db()
        contact = db.get_contact(data.contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        if not data.template_id:
            return {"subject": "", "body": "", "template_name": None}

        from src.email.email_templates import TemplateManager, get_template_variables
        from src.email.email_personalizer import EmailPersonalizer

        manager = TemplateManager()
        template = manager.get_template(data.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        job = db.get_job(data.job_id) if data.job_id else None

        applicant = None
        try:
            from src.core.applicant import Applicant
            profile_path = paths.profile_path()
            if profile_path.exists():
                applicant = Applicant.from_file(profile_path)
        except Exception as e:
            logger.warning(f"Could not load applicant profile: {e}")
            pass

        variables = get_template_variables(contact, job, applicant)
        personalizer = EmailPersonalizer()
        variables["personalized_hook"] = personalizer._get_fallback_hook(contact)

        subject, body = manager.render_template(template, variables)

        return {"subject": subject, "body": body, "template_name": template.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering email template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to render template: {str(e)}")


@router.get("/api/emails/{email_id}")
async def get_email(email_id: str):
    """Get a specific email"""
    db = get_db()
    email = db.get_cold_email(email_id)

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    return {
        "id": email.id,
        "contact_id": email.contact_id,
        "job_id": email.job_id,
        "subject": email.subject,
        "body": email.body,
        "status": email.status.value if hasattr(email.status, 'value') else email.status,
        "scheduled_at": email.scheduled_at.isoformat() if email.scheduled_at else None,
        "sent_at": email.sent_at.isoformat() if email.sent_at else None,
        "personalization_data": email.personalization_data,
    }


@router.patch("/api/emails/{email_id}", dependencies=[Depends(require_admin)])
async def update_email(email_id: str, update: EmailUpdate):
    """Update email fields (subject, body, status, scheduled_at)"""
    db = get_db()
    update_data: dict = {}
    if update.subject is not None:
        update_data["subject"] = update.subject
    if update.body is not None:
        update_data["body"] = update.body
    if update.status is not None:
        update_data["status"] = update.status
    if update.scheduled_at is not None:
        try:
            update_data["scheduled_at"] = datetime.fromisoformat(update.scheduled_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = db.update_cold_email_fields(email_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"success": True}


@router.delete("/api/emails/{email_id}", dependencies=[Depends(require_admin)])
async def delete_email(email_id: str):
    """Delete a cold email"""
    db = get_db()
    success = db.delete_cold_email(email_id)
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"success": True}


@router.post("/api/emails/{email_id}/send", dependencies=[Depends(require_admin)])
async def send_email_now(email_id: str, background_tasks: BackgroundTasks):
    """Send a specific email immediately"""

    async def run_send():
        try:
            from src.email.cold_email_service import get_cold_email_service
            service = get_cold_email_service()
            success = await service.send_email_now(email_id)
            logger.error(f"   {'✅' if success else '❌'} Send email {email_id}: {'success' if success else 'failed'}")
        except Exception as e:
            logger.error(f"   ❌ Send error: {e}")

    background_tasks.add_task(run_send)
    return {"status": "sending", "email_id": email_id}


@router.post("/api/emails/{email_id}/schedule", dependencies=[Depends(require_admin)])
async def schedule_email(email_id: str):
    """Schedule an email for optimal delivery time"""
    from src.email.email_scheduler import EmailScheduler
    from src.core.cold_email_models import EmailStatus

    db = get_db()
    email = db.get_cold_email(email_id)

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    scheduler = EmailScheduler()
    scheduled_time = scheduler.schedule_email(email)

    db.update_cold_email_status(email_id, EmailStatus.SCHEDULED)

    return {
        "success": True,
        "email_id": email_id,
        "scheduled_at": scheduled_time.isoformat()
    }


# ============ Templates ============

@router.get("/api/templates")
async def list_templates():
    """Get all email templates"""
    from src.email.email_templates import TemplateManager

    manager = TemplateManager()
    templates = manager.get_all_templates()

    return {
        "total": len(templates),
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "subject": t.subject,
                "persona_type": t.persona_type.value if t.persona_type else None,
                "is_followup": t.is_followup,
                "followup_day": t.followup_day,
            }
            for t in templates
        ]
    }


@router.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template with full body"""
    from src.email.email_templates import TemplateManager

    manager = TemplateManager()
    template = manager.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "subject": template.subject,
        "body": template.body,
        "persona_type": template.persona_type.value if template.persona_type else None,
        "is_followup": template.is_followup,
        "followup_day": template.followup_day,
    }


# ============ Campaigns / stats / processing ============

@router.post("/api/campaigns", dependencies=[Depends(require_admin)])
async def create_campaign(campaign_in: CampaignCreate, background_tasks: BackgroundTasks):
    """Create a cold email campaign for a job"""

    async def run_campaign():
        try:
            from src.email.cold_email_service import get_cold_email_service
            from src.core.cold_email_models import ContactPersona

            db = get_db()
            job = db.get_job(campaign_in.job_id)

            if not job:
                logger.error(f"   ❌ Job {campaign_in.job_id} not found")
                return

            personas = None
            if campaign_in.personas:
                personas = [ContactPersona(p) for p in campaign_in.personas]

            service = get_cold_email_service()
            result = await service.create_campaign_for_job(
                job=job,
                max_contacts=campaign_in.max_contacts,
                personas=personas
            )
            logger.info(f"   ✅ Campaign created: {result}")
        except Exception as e:
            logger.error(f"   ❌ Campaign error: {e}")

    background_tasks.add_task(run_campaign)
    return {"status": "started", "job_id": campaign_in.job_id}


@router.get("/api/email-stats")
async def get_email_stats():
    """Get cold email statistics"""
    db = get_db()
    stats = db.get_email_stats()

    return {
        "total_emails": stats["total"],
        "sent": stats["sent"],
        "opened": stats["opened"],
        "replied": stats["replied"],
        "scheduled": stats["scheduled"],
        "open_rate": round(stats["open_rate"], 1),
        "reply_rate": round(stats["reply_rate"], 1),
    }


@router.post("/api/emails/process", dependencies=[Depends(require_admin)])
async def process_scheduled_emails(background_tasks: BackgroundTasks):
    """Process all scheduled emails that are due"""

    async def run_process():
        try:
            from src.email.cold_email_service import get_cold_email_service
            service = get_cold_email_service()
            result = await service.process_scheduled()
            logger.info(f"   ✅ Processed emails: {result}")
        except Exception as e:
            logger.error(f"   ❌ Process error: {e}")

    background_tasks.add_task(run_process)
    return {"status": "started", "message": "Processing scheduled emails"}
