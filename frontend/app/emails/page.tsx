'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/Sidebar';
import { api, Profile, Gamification, Contact, Email, Job, Template, EmailStats } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function EmailsPage() {
  // ==================== STATE ====================
  const [profile, setProfile] = useState<Profile | null>(null);
  const [gamification, setGamification] = useState<Gamification | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [emails, setEmails] = useState<Email[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [emailStats, setEmailStats] = useState<EmailStats | null>(null);
  const [loading, setLoading] = useState(true);

  // UI
  const [activeTab, setActiveTab] = useState<'contacts' | 'compose' | 'outbox' | 'templates'>('contacts');
  const [search, setSearch] = useState('');
  const [jobFilter, setJobFilter] = useState('');
  const [emailStatusFilter, setEmailStatusFilter] = useState('all');
  const [selectedTemplateContact, setSelectedTemplateContact] = useState<string>('');
  const [templatePreview, setTemplatePreview] = useState<{ templateId: string; subject: string; body: string } | null>(null);

  // Compose
  const [composeContactId, setComposeContactId] = useState('');
  const [composeJobId, setComposeJobId] = useState('');
  const [composeTemplateId, setComposeTemplateId] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [editingEmailId, setEditingEmailId] = useState<string | null>(null);

  // Modals
  const [showAddContact, setShowAddContact] = useState(false);
  const [showFindContacts, setShowFindContacts] = useState(false);
  const [findContactsMode, setFindContactsMode] = useState<'company' | 'job'>('company');
  const [findContactsCompany, setFindContactsCompany] = useState('');
  const [findContactsJobId, setFindContactsJobId] = useState('');
  const [isScraping, setIsScraping] = useState(false);
  const [previewEmail, setPreviewEmail] = useState<Email | null>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleEmailId, setScheduleEmailId] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [confirmDelete, setConfirmDelete] = useState<{ type: 'contact' | 'email'; id: string } | null>(null);

  // Contact form
  const [contactForm, setContactForm] = useState({
    name: '', email: '', title: '', company: '', persona: 'unknown',
    linkedin_url: '', job_id: '', notes: ''
  });

  // Bulk email selection
  const [selectedContacts, setSelectedContacts] = useState<Set<string>>(new Set());
  const [bulkComposeMode, setBulkComposeMode] = useState(false);
  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [quickAddForm, setQuickAddForm] = useState({ name: '', email: '', company: '' });

  // Toast
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' as 'success' | 'error' });
  const { isAdmin } = useAuth();

  // ==================== HELPERS ====================
  const notify = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast(prev => ({ ...prev, show: false })), 3000);
  };

  const statusStyle = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'text-[var(--valo-text-dim)] border-[var(--valo-text-dim)] bg-[var(--valo-text-dim)]/10',
      scheduled: 'text-[var(--valo-yellow)] border-[var(--valo-yellow)] bg-[var(--valo-yellow)]/10',
      sent: 'text-[var(--valo-green)] border-[var(--valo-green)] bg-[var(--valo-green)]/10',
      opened: 'text-[var(--valo-cyan)] border-[var(--valo-cyan)] bg-[var(--valo-cyan)]/10',
      replied: 'text-[var(--valo-purple)] border-[var(--valo-purple)] bg-[var(--valo-purple)]/10',
      bounced: 'text-[var(--valo-orange)] border-[var(--valo-orange)] bg-[var(--valo-orange)]/10',
      failed: 'text-[var(--valo-red)] border-[var(--valo-red)] bg-[var(--valo-red)]/10',
    };
    return styles[status] || styles.draft;
  };

  const personaLabel = (p: string) => {
    const labels: Record<string, string> = {
      recruiter: 'RECRUITER', hiring_manager: 'HIRING MGR', engineering_manager: 'ENG MGR',
      hr: 'HR', talent_acquisition: 'TALENT ACQ', unknown: 'OTHER'
    };
    return labels[p] || 'OTHER';
  };

  // ==================== DATA FETCHING ====================
  const fetchContacts = useCallback(async () => {
    try {
      const params: Record<string, string | number> = { limit: 200 };
      if (search) params.search = search;
      if (jobFilter) params.job_id = jobFilter;
      const res = await api.getContacts(params);
      setContacts(res.contacts);
    } catch (e) { console.error(e); }
  }, [search, jobFilter]);

  const fetchEmails = useCallback(async () => {
    try {
      const params: Record<string, string | number> = { limit: 200 };
      if (search) params.search = search;
      if (jobFilter) params.job_id = jobFilter;
      if (emailStatusFilter !== 'all') params.status = emailStatusFilter;
      const res = await api.getEmails(params);
      setEmails(res.emails);
    } catch (e) { console.error(e); }
  }, [search, jobFilter, emailStatusFilter]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [p, g, tRes, jRes, stats] = await Promise.all([
        api.getProfile(), api.getGamification(),
        api.getTemplates(), api.getJobs({ per_page: 50, sort: 'newest' }),
        api.getEmailStats()
      ]);
      setProfile(p);
      setGamification(g);
      setTemplates(tRes.templates);
      setJobs(jRes.jobs);
      setEmailStats(stats);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => { fetchContacts(); }, [fetchContacts]);
  useEffect(() => { fetchEmails(); }, [fetchEmails]);

  // ==================== HANDLERS ====================
  const handleAddContact = async () => {
    if (!contactForm.name || !contactForm.email || !contactForm.company) {
      notify('Name, email, and company are required', 'error');
      return;
    }
    try {
      await api.createContact(contactForm);
      setShowAddContact(false);
      setContactForm({ name: '', email: '', title: '', company: '', persona: 'unknown', linkedin_url: '', job_id: '', notes: '' });
      fetchContacts();
      notify('CONTACT REGISTERED');
    } catch (e) { notify('Failed to add contact', 'error'); }
  };

  const handleFindContacts = async () => {
    if (findContactsMode === 'company' && !findContactsCompany.trim()) {
      notify('Enter a company name', 'error');
      return;
    }
    if (findContactsMode === 'job' && !findContactsJobId) {
      notify('Select a job', 'error');
      return;
    }
    
    setIsScraping(true);
    try {
      await api.scrapeContacts({
        company: findContactsMode === 'company' ? findContactsCompany : undefined,
        job_id: findContactsMode === 'job' ? findContactsJobId : undefined,
        limit: 20,
      });
      notify('SCAN INITIATED - Contacts will appear shortly');
      setShowFindContacts(false);
      setFindContactsCompany('');
      setFindContactsJobId('');
      // Refresh contacts after a delay
      setTimeout(() => {
        fetchContacts();
      }, 3000);
    } catch (e) {
      notify('Failed to start scan', 'error');
    } finally {
      setIsScraping(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!confirmDelete) return;
    try {
      if (confirmDelete.type === 'contact') {
        await api.deleteContact(confirmDelete.id);
        fetchContacts();
        notify('CONTACT REMOVED');
      } else {
        await api.deleteEmail(confirmDelete.id);
        fetchEmails();
        notify('EMAIL DELETED');
      }
    } catch (e) { notify('Delete failed', 'error'); }
    setConfirmDelete(null);
  };

  const handleTemplateChange = async (templateId: string) => {
    setComposeTemplateId(templateId);
    if (!templateId) return;
    
    // If no contact selected, just set template ID and let user select contact
    if (!composeContactId) {
      notify('Select a contact first to preview template', 'error');
      return;
    }
    
    try {
      const res = await api.renderEmail({
        contact_id: composeContactId,
        job_id: composeJobId || undefined,
        template_id: templateId,
      });
      setComposeSubject(res.subject);
      setComposeBody(res.body);
      notify('Template applied successfully');
    } catch (e: any) {
      console.error('Template render error:', e);
      const errorMsg = e?.message || 'Failed to render template';
      notify(errorMsg, 'error');
      // Still set template ID so user can manually edit
    }
  };

  const handleSaveDraft = async () => {
    if (!composeContactId || !composeSubject) {
      notify('Select a contact and enter a subject', 'error');
      return;
    }
    try {
      if (editingEmailId) {
        await api.updateEmail(editingEmailId, { subject: composeSubject, body: composeBody });
        notify('DRAFT UPDATED');
      } else {
        await api.createEmail({
          contact_id: composeContactId,
          job_id: composeJobId || undefined,
          template_id: composeTemplateId || undefined,
          subject: composeSubject,
          body: composeBody,
        });
        notify('DRAFT SAVED');
      }
      resetCompose();
      fetchEmails();
    } catch (e) { notify('Failed to save draft', 'error'); }
  };

  const handleSendNow = async () => {
    if (!composeContactId || !composeSubject) {
      notify('Select a contact and enter a subject', 'error');
      return;
    }
    try {
      let emailId = editingEmailId;
      if (!emailId) {
        const res = await api.createEmail({
          contact_id: composeContactId,
          job_id: composeJobId || undefined,
          template_id: composeTemplateId || undefined,
          subject: composeSubject,
          body: composeBody,
        });
        emailId = res.id;
      } else {
        await api.updateEmail(emailId, { subject: composeSubject, body: composeBody });
      }
      await api.sendEmailNow(emailId);
      notify('EMAIL DISPATCHED');
      resetCompose();
      fetchEmails();
    } catch (e) { notify('Send failed', 'error'); }
  };

  // Quick send to contact (uses first template or default)
  const handleQuickSend = async (contact: Contact) => {
    try {
      const defaultTemplate = templates.find(t => !t.is_followup);
      let subject = '';
      let body = '';
      
      if (defaultTemplate) {
        const rendered = await api.renderEmail({
          contact_id: contact.id,
          job_id: contact.job_id || undefined,
          template_id: defaultTemplate.id,
        });
        subject = rendered.subject;
        body = rendered.body;
      } else {
        subject = `Re: ${contact.company} - Application`;
        body = `Hi ${contact.name},\n\nI'm reaching out regarding opportunities at ${contact.company}...`;
      }
      
      const res = await api.createEmail({
        contact_id: contact.id,
        job_id: contact.job_id || undefined,
        template_id: defaultTemplate?.id,
        subject,
        body,
      });
      await api.sendEmailNow(res.id);
      notify(`EMAIL SENT TO ${contact.name.toUpperCase()}`);
      fetchEmails();
    } catch (e) {
      notify('Quick send failed', 'error');
    }
  };

  // Bulk send
  const handleBulkSend = async () => {
    if (selectedContacts.size === 0) {
      notify('Select contacts to send bulk email', 'error');
      return;
    }
    if (!composeSubject || !composeBody) {
      notify('Enter subject and body for bulk email', 'error');
      return;
    }
    
    const contactIds = Array.from(selectedContacts);
    let successCount = 0;
    let failCount = 0;
    
    for (const contactId of contactIds) {
      try {
        const res = await api.createEmail({
          contact_id: contactId,
          job_id: composeJobId || undefined,
          template_id: composeTemplateId || undefined,
          subject: composeSubject,
          body: composeBody,
        });
        await api.sendEmailNow(res.id);
        successCount++;
      } catch (e) {
        failCount++;
      }
    }
    
    notify(`BULK SEND: ${successCount} SENT, ${failCount} FAILED`);
    setSelectedContacts(new Set());
    setBulkComposeMode(false);
    resetCompose();
    fetchEmails();
  };

  // Quick add contact
  const handleQuickAdd = async () => {
    if (!quickAddForm.name || !quickAddForm.email || !quickAddForm.company) {
      notify('Name, email, and company required', 'error');
      return;
    }
    try {
      await api.createContact({
        name: quickAddForm.name,
        email: quickAddForm.email,
        company: quickAddForm.company,
      });
      setQuickAddForm({ name: '', email: '', company: '' });
      setShowQuickAdd(false);
      fetchContacts();
      notify('CONTACT ADDED');
    } catch (e) {
      notify('Failed to add contact', 'error');
    }
  };

  // Quick apply template and send/schedule
  const handleTemplateQuickAction = async (templateId: string, action: 'send' | 'schedule' | 'compose') => {
    if (!selectedTemplateContact) {
      notify('Select a contact first', 'error');
      return;
    }
    
    try {
      const res = await api.renderEmail({
        contact_id: selectedTemplateContact,
        job_id: jobFilter || undefined,
        template_id: templateId,
      });
      
      if (action === 'send') {
        const emailRes = await api.createEmail({
          contact_id: selectedTemplateContact,
          job_id: jobFilter || undefined,
          template_id: templateId,
          subject: res.subject,
          body: res.body,
        });
        await api.sendEmailNow(emailRes.id);
        notify('EMAIL SENT');
        fetchEmails();
      } else if (action === 'schedule') {
        const emailRes = await api.createEmail({
          contact_id: selectedTemplateContact,
          job_id: jobFilter || undefined,
          template_id: templateId,
          subject: res.subject,
          body: res.body,
        });
        await api.scheduleEmail(emailRes.id);
        notify('EMAIL SCHEDULED');
        fetchEmails();
      } else {
        // Compose mode - fill the compose form
        setComposeContactId(selectedTemplateContact);
        setComposeJobId(jobFilter || '');
        setComposeTemplateId(templateId);
        setComposeSubject(res.subject);
        setComposeBody(res.body);
        setActiveTab('compose');
      }
      setSelectedTemplateContact('');
    } catch (e) {
      notify('Failed to apply template', 'error');
    }
  };

  // Apply template to compose form
  const handleApplyTemplate = async (templateId: string, contactId?: string) => {
    const targetContactId = contactId || composeContactId;
    if (!targetContactId) {
      notify('Select a contact first', 'error');
      return;
    }
    
    try {
      const res = await api.renderEmail({
        contact_id: targetContactId,
        job_id: composeJobId || jobFilter || undefined,
        template_id: templateId,
      });
      setComposeTemplateId(templateId);
      setComposeContactId(targetContactId);
      setComposeSubject(res.subject);
      setComposeBody(res.body);
      setActiveTab('compose');
      notify('TEMPLATE APPLIED');
    } catch (e) {
      notify('Failed to apply template', 'error');
    }
  };

  const handleScheduleFromCompose = async () => {
    if (!composeContactId || !composeSubject) {
      notify('Select contact and enter subject', 'error');
      return;
    }
    try {
      let eid = editingEmailId;
      if (!eid) {
        const res = await api.createEmail({
          contact_id: composeContactId,
          job_id: composeJobId || undefined,
          subject: composeSubject,
          body: composeBody,
        });
        eid = res.id;
      } else {
        await api.updateEmail(eid, { subject: composeSubject, body: composeBody });
      }
      const schedRes = await api.scheduleEmail(eid);
      notify(`SCHEDULED: ${new Date(schedRes.scheduled_at).toLocaleString()}`);
      resetCompose();
      fetchEmails();
    } catch (e) { notify('Schedule failed', 'error'); }
  };

  const handleScheduleAuto = async (emailId: string) => {
    try {
      const res = await api.scheduleEmail(emailId);
      notify(`SCHEDULED: ${new Date(res.scheduled_at).toLocaleString()}`);
      fetchEmails();
    } catch (e) { notify('Schedule failed', 'error'); }
  };

  const handleScheduleCustom = async () => {
    if (!scheduleEmailId || !scheduleTime) return;
    try {
      await api.updateEmail(scheduleEmailId, {
        status: 'scheduled',
        scheduled_at: new Date(scheduleTime).toISOString(),
      });
      setShowScheduleModal(false);
      setScheduleEmailId('');
      setScheduleTime('');
      fetchEmails();
      notify('SCHEDULED');
    } catch (e) { notify('Schedule failed', 'error'); }
  };

  const handleEditEmail = (email: Email) => {
    setEditingEmailId(email.id);
    setComposeContactId(email.contact_id);
    setComposeJobId(email.job_id || '');
    setComposeTemplateId(email.template_id || '');
    setComposeSubject(email.subject);
    setComposeBody(email.body);
    setActiveTab('compose');
  };

  const handleComposeFor = (contact: Contact) => {
    setComposeContactId(contact.id);
    setComposeJobId(contact.job_id || '');
    setEditingEmailId(null);
    setComposeSubject('');
    setComposeBody('');
    setComposeTemplateId('');
    setActiveTab('compose');
  };

  const resetCompose = () => {
    setComposeContactId('');
    setComposeJobId('');
    setComposeTemplateId('');
    setComposeSubject('');
    setComposeBody('');
    setShowPreview(false);
    setEditingEmailId(null);
    setBulkComposeMode(false);
    setSelectedContacts(new Set());
  };

  // ==================== RENDER ====================
  const statCards = [
    { label: 'CONTACTS', value: contacts.length, color: 'var(--valo-cyan)' },
    { label: 'DRAFTS', value: emails.filter(e => e.status === 'draft').length, color: 'var(--valo-text-dim)' },
    { label: 'SCHEDULED', value: emailStats?.scheduled || 0, color: 'var(--valo-yellow)' },
    { label: 'SENT', value: emailStats?.sent || 0, color: 'var(--valo-green)' },
    { label: 'REPLY RATE', value: `${emailStats?.reply_rate?.toFixed(0) || 0}%`, color: 'var(--valo-purple)' },
  ];

  return (
    <div className="flex min-h-screen bg-[var(--valo-darker)]">
      <Sidebar
        agentName={profile?.agent_name || 'AGENT'}
        userName={profile?.full_name || profile?.first_name}
        valorantAgent={profile?.valorant_agent || 'jett'}
        levelTitle={gamification?.level_title || 'RECRUIT'}
        level={gamification?.level || 1}
        rankIcon={gamification?.rank_icon}
        onDeploy={() => {}}
        isDeploying={false}
      />

      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <main className="flex-1 p-8 overflow-y-auto">
          {loading ? (
            <div className="text-center py-20">
              <svg className="w-8 h-8 animate-spin mx-auto mb-4 text-[var(--valo-cyan)]" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <div className="text-[var(--valo-text-dim)] tracking-widest text-sm">INITIALIZING COMMS...</div>
            </div>
          ) : !isAdmin ? (
            <div className="flex flex-col items-center justify-center py-32">
              <div className="tech-border p-12 text-center max-w-lg">
                <div className="text-6xl mb-6">🔒</div>
                <h2 className="font-display text-3xl font-bold tracking-wider text-[var(--valo-text)] mb-3">
                  ADMIN ACCESS REQUIRED
                </h2>
                <p className="text-[var(--valo-text-dim)] text-sm tracking-wide mb-2">
                  The Outreach Center contains sensitive contact information and email capabilities.
                </p>
                <p className="text-[var(--valo-text-dim)] text-sm tracking-wide">
                  Login as admin from the sidebar to access this section.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* HEADER */}
              <header className="mb-6">
                <div className="flex items-center gap-2 text-[var(--valo-text-dim)] text-sm mb-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--valo-cyan)] pulse-green" />
                  COMMUNICATIONS // COLD OUTREACH
                </div>
                <h1 className="font-display text-4xl font-bold tracking-wider text-[var(--valo-text)]">
                  OUTREACH CENTER
                </h1>
              </header>

              {/* STATS */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
                {statCards.map(s => (
                  <div key={s.label} className="tech-border p-4 text-center">
                    <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
                    <div className="text-[10px] text-[var(--valo-text-dim)] tracking-widest mt-1">{s.label}</div>
                  </div>
                ))}
              </div>

              {/* SEARCH + FILTER */}
              <div className="flex gap-3 mb-6">
                <div className="flex-1 relative">
                  <svg className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--valo-text-dim)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search contacts, emails, companies..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    className="w-full bg-black/30 border border-[var(--valo-gray)] pl-10 pr-4 py-2.5 text-[var(--valo-text)] placeholder-[var(--valo-text-dim)] outline-none focus:border-[var(--valo-cyan)] transition font-mono text-sm"
                  />
                </div>
                <select
                  value={jobFilter}
                  onChange={e => setJobFilter(e.target.value)}
                  className="bg-black/30 border border-[var(--valo-gray)] px-4 py-2.5 text-[var(--valo-text)] outline-none focus:border-[var(--valo-cyan)] text-sm min-w-[200px]"
                >
                  <option value="">ALL JOBS</option>
                  {jobs.map(j => (
                    <option key={j.id} value={j.id}>{j.title} @ {j.company}</option>
                  ))}
                </select>
              </div>

              {/* TABS */}
              <div className="flex gap-6 mb-6 border-b border-[var(--valo-gray-light)] pb-1">
                {(['contacts', 'templates', 'compose', 'outbox'] as const).map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`pb-3 px-2 font-bold tracking-widest text-sm transition-all ${
                      activeTab === tab
                        ? tab === 'contacts' ? 'text-[var(--valo-cyan)] border-b-2 border-[var(--valo-cyan)]'
                          : tab === 'templates' ? 'text-[var(--valo-yellow)] border-b-2 border-[var(--valo-yellow)]'
                          : tab === 'compose' ? 'text-[var(--valo-purple)] border-b-2 border-[var(--valo-purple)]'
                          : 'text-[var(--valo-red)] border-b-2 border-[var(--valo-red)]'
                        : 'text-[var(--valo-text-dim)] hover:text-[var(--valo-text)]'
                    }`}
                  >
                    {tab.toUpperCase()}
                    {tab === 'contacts' && ` (${contacts.length})`}
                    {tab === 'templates' && ` (${templates.filter(t => !t.is_followup).length})`}
                    {tab === 'outbox' && ` (${emails.length})`}
                  </button>
                ))}
              </div>

              {/* ==================== CONTACTS TAB ==================== */}
              {activeTab === 'contacts' && (
                <div>
                  {/* Quick Add Inline Form */}
                  {showQuickAdd && (
                    <div className="tech-border p-4 mb-4 bg-[var(--valo-dark)]/50 border-[var(--valo-cyan)]">
                      <div className="grid grid-cols-3 gap-3 mb-3">
                        <input
                          type="text"
                          placeholder="Name *"
                          value={quickAddForm.name}
                          onChange={e => setQuickAddForm({ ...quickAddForm, name: e.target.value })}
                          className="bg-black/30 border border-[var(--valo-gray)] px-3 py-2 text-[var(--valo-text)] outline-none focus:border-[var(--valo-cyan)] text-sm"
                          onKeyDown={e => e.key === 'Enter' && handleQuickAdd()}
                        />
                        <input
                          type="email"
                          placeholder="Email *"
                          value={quickAddForm.email}
                          onChange={e => setQuickAddForm({ ...quickAddForm, email: e.target.value })}
                          className="bg-black/30 border border-[var(--valo-gray)] px-3 py-2 text-[var(--valo-text)] outline-none focus:border-[var(--valo-cyan)] text-sm font-mono"
                          onKeyDown={e => e.key === 'Enter' && handleQuickAdd()}
                        />
                        <input
                          type="text"
                          placeholder="Company *"
                          value={quickAddForm.company}
                          onChange={e => setQuickAddForm({ ...quickAddForm, company: e.target.value })}
                          className="bg-black/30 border border-[var(--valo-gray)] px-3 py-2 text-[var(--valo-text)] outline-none focus:border-[var(--valo-cyan)] text-sm"
                          onKeyDown={e => e.key === 'Enter' && handleQuickAdd()}
                        />
                      </div>
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => { setShowQuickAdd(false); setQuickAddForm({ name: '', email: '', company: '' }); }}
                          className="text-[var(--valo-text-dim)] hover:text-white text-xs font-bold"
                        >
                          CANCEL
                        </button>
                        <button
                          onClick={handleQuickAdd}
                          className="bg-[var(--valo-cyan)] text-black px-4 py-1.5 text-xs font-bold hover:brightness-110"
                        >
                          ADD
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between items-center mb-4 flex-wrap gap-3">
                    <div className="flex gap-3">
                      {selectedContacts.size > 0 && (
                        <>
                          <button
                            onClick={() => { setBulkComposeMode(true); setActiveTab('compose'); }}
                            className="bg-[var(--valo-purple)] text-white px-4 py-2 text-xs font-bold tracking-wider hover:brightness-110"
                          >
                            BULK EMAIL ({selectedContacts.size})
                          </button>
                          <button
                            onClick={() => setSelectedContacts(new Set())}
                            className="text-[var(--valo-text-dim)] hover:text-white text-xs font-bold"
                          >
                            CLEAR
                          </button>
                        </>
                      )}
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => setShowFindContacts(true)}
                        className="bg-transparent border border-[var(--valo-cyan)] text-[var(--valo-cyan)] px-6 py-2.5 font-bold tracking-wider text-sm tech-button hover:bg-[var(--valo-cyan)] hover:text-black transition-all"
                        style={{ clipPath: 'polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%)' }}
                      >
                        🔍 FIND CONTACTS
                      </button>
                      <button
                        onClick={() => setShowQuickAdd(!showQuickAdd)}
                        className="bg-[var(--valo-cyan)] text-black px-6 py-2.5 font-bold tracking-wider text-sm hover:brightness-110 transition"
                        style={{ clipPath: 'polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)' }}
                      >
                        {showQuickAdd ? '✕ CANCEL' : '+ QUICK ADD'}
                      </button>
                      <button
                        onClick={() => setShowAddContact(true)}
                        className="bg-transparent border border-[var(--valo-gray)] text-[var(--valo-text)] px-4 py-2.5 font-bold tracking-wider text-sm hover:border-[var(--valo-cyan)] transition"
                      >
                        FULL FORM
                      </button>
                    </div>
                  </div>

                  {contacts.length === 0 ? (
                    <div className="tech-border p-12 text-center">
                      <div className="text-5xl mb-4">&#128225;</div>
                      <div className="text-xl text-[var(--valo-text)] mb-2">NO CONTACTS IN DATABASE</div>
                      <div className="text-[var(--valo-text-dim)] mb-6">Add contacts manually to start your outreach campaign</div>
                      <button
                        onClick={() => setShowAddContact(true)}
                        className="bg-[var(--valo-cyan)] text-black px-8 py-3 font-bold tracking-wider hover:brightness-110"
                      >
                        ADD FIRST CONTACT
                      </button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-8">
                      <AnimatePresence mode="popLayout">
                        {contacts.map((c, i) => (
                          <motion.div
                            key={c.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ delay: Math.min(i * 0.03, 0.3) }}
                            className={`tech-border p-5 bg-[var(--valo-dark)]/30 border-l-4 border-l-[var(--valo-cyan)] hover:bg-[var(--valo-dark)]/50 transition-colors ${
                              selectedContacts.has(c.id) ? 'ring-2 ring-[var(--valo-purple)]' : ''
                            }`}
                          >
                            <div className="flex justify-between items-start mb-3">
                              <div className="flex items-start gap-2 flex-1">
                                <input
                                  type="checkbox"
                                  checked={selectedContacts.has(c.id)}
                                  onChange={e => {
                                    const newSet = new Set(selectedContacts);
                                    if (e.target.checked) {
                                      newSet.add(c.id);
                                    } else {
                                      newSet.delete(c.id);
                                    }
                                    setSelectedContacts(newSet);
                                  }}
                                  className="mt-1 w-4 h-4 accent-[var(--valo-purple)] cursor-pointer"
                                />
                                <div className="flex-1">
                                  <h3 className="font-bold text-[var(--valo-text)] text-lg">{c.name}</h3>
                                  {c.title && <p className="text-sm text-[var(--valo-cyan)]">{c.title}</p>}
                                  <p className="text-xs text-[var(--valo-text-dim)] uppercase tracking-wide">{c.company}</p>
                                </div>
                              </div>
                              <div className="flex gap-1.5 flex-shrink-0">
                                <span className="px-2 py-0.5 text-[10px] font-bold tracking-wide border border-[var(--valo-cyan)]/30 text-[var(--valo-cyan)]">
                                  {personaLabel(c.persona)}
                                </span>
                                <span className="px-2 py-0.5 text-[10px] font-bold tracking-wide border border-[var(--valo-text-dim)]/30 text-[var(--valo-text-dim)]">
                                  {c.source?.toUpperCase() || 'MANUAL'}
                                </span>
                              </div>
                            </div>
                            <div className="font-mono text-sm text-[var(--valo-text-dim)] mb-3">{c.email}</div>
                            {c.notes && <p className="text-xs text-[var(--valo-text-dim)] mb-3 italic">{c.notes}</p>}
                            <div className="flex gap-2 items-center flex-wrap">
                              <button
                                onClick={() => handleQuickSend(c)}
                                className="flex-1 bg-[var(--valo-green)]/20 border border-[var(--valo-green)]/50 text-[var(--valo-green)] px-3 py-1.5 text-xs font-bold tracking-wider hover:bg-[var(--valo-green)]/30 transition"
                                title="Quick send with default template"
                              >
                                ⚡ QUICK SEND
                              </button>
                              {templates.filter(t => !t.is_followup).length > 0 && (
                                <div className="relative group">
                                  <button
                                    className="bg-[var(--valo-yellow)]/20 border border-[var(--valo-yellow)]/50 text-[var(--valo-yellow)] px-3 py-1.5 text-xs font-bold tracking-wider hover:bg-[var(--valo-yellow)]/30 transition"
                                  >
                                    📋 TEMPLATE
                                  </button>
                                  <div className="absolute right-0 top-full mt-1 w-64 bg-[var(--valo-dark)] border border-[var(--valo-yellow)] shadow-lg z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                                    <div className="p-2 max-h-64 overflow-y-auto">
                                      {templates.filter(t => !t.is_followup).slice(0, 5).map(t => (
                                        <div key={t.id} className="mb-2 last:mb-0">
                                          <div className="text-xs font-bold text-[var(--valo-text)] mb-1">{t.name}</div>
                                          <div className="flex gap-1">
                                            <button
                                              onClick={async () => {
                                                try {
                                                  const res = await api.renderEmail({
                                                    contact_id: c.id,
                                                    job_id: c.job_id || undefined,
                                                    template_id: t.id,
                                                  });
                                                  const emailRes = await api.createEmail({
                                                    contact_id: c.id,
                                                    job_id: c.job_id || undefined,
                                                    template_id: t.id,
                                                    subject: res.subject,
                                                    body: res.body,
                                                  });
                                                  await api.sendEmailNow(emailRes.id);
                                                  notify(`EMAIL SENT TO ${c.name.toUpperCase()}`);
                                                  fetchEmails();
                                                } catch (e) {
                                                  notify('Send failed', 'error');
                                                }
                                              }}
                                              className="flex-1 bg-[var(--valo-green)]/20 border border-[var(--valo-green)]/50 text-[var(--valo-green)] px-2 py-1 text-[10px] font-bold hover:bg-[var(--valo-green)]/30"
                                            >
                                              SEND
                                            </button>
                                            <button
                                              onClick={async () => {
                                                try {
                                                  const res = await api.renderEmail({
                                                    contact_id: c.id,
                                                    job_id: c.job_id || undefined,
                                                    template_id: t.id,
                                                  });
                                                  const emailRes = await api.createEmail({
                                                    contact_id: c.id,
                                                    job_id: c.job_id || undefined,
                                                    template_id: t.id,
                                                    subject: res.subject,
                                                    body: res.body,
                                                  });
                                                  await api.scheduleEmail(emailRes.id);
                                                  notify(`EMAIL SCHEDULED FOR ${c.name.toUpperCase()}`);
                                                  fetchEmails();
                                                } catch (e) {
                                                  notify('Schedule failed', 'error');
                                                }
                                              }}
                                              className="flex-1 bg-[var(--valo-yellow)]/20 border border-[var(--valo-yellow)]/50 text-[var(--valo-yellow)] px-2 py-1 text-[10px] font-bold hover:bg-[var(--valo-yellow)]/30"
                                            >
                                              SCHEDULE
                                            </button>
                                          </div>
                                        </div>
                                      ))}
                                      {templates.filter(t => !t.is_followup).length > 5 && (
                                        <button
                                          onClick={() => {
                                            setSelectedTemplateContact(c.id);
                                            setActiveTab('templates');
                                          }}
                                          className="w-full mt-2 bg-[var(--valo-purple)]/20 border border-[var(--valo-purple)]/50 text-[var(--valo-purple)] px-2 py-1 text-[10px] font-bold hover:bg-[var(--valo-purple)]/30"
                                        >
                                          VIEW ALL ({templates.filter(t => !t.is_followup).length})
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )}
                              <button
                                onClick={() => handleComposeFor(c)}
                                className="flex-1 bg-[var(--valo-purple)]/20 border border-[var(--valo-purple)]/50 text-[var(--valo-purple)] px-3 py-1.5 text-xs font-bold tracking-wider hover:bg-[var(--valo-purple)]/30 transition"
                              >
                                COMPOSE
                              </button>
                              {c.linkedin_url && (
                                <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                                  className="text-[var(--valo-text-dim)] hover:text-[var(--valo-cyan)] p-1.5">
                                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" /></svg>
                                </a>
                              )}
                              <button
                                onClick={() => setConfirmDelete({ type: 'contact', id: c.id })}
                                className="text-[var(--valo-text-dim)] hover:text-[var(--valo-red)] p-1.5 transition"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                              </button>
                            </div>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                    </div>
                  )}
                </div>
              )}

              {/* ==================== TEMPLATES TAB ==================== */}
              {activeTab === 'templates' && (
                <div>
                  {/* Quick Contact Selector */}
                  <div className="mb-6 p-4 tech-border bg-[var(--valo-dark)]/30 border-[var(--valo-yellow)]/30">
                    <div className="flex items-center gap-4 flex-wrap">
                      <label className="text-xs text-[var(--valo-text-dim)] tracking-widest">QUICK ACTION MODE:</label>
                      <select
                        value={selectedTemplateContact}
                        onChange={e => setSelectedTemplateContact(e.target.value)}
                        className="flex-1 min-w-[300px] bg-black/30 border border-[var(--valo-gray)] px-3 py-2 text-[var(--valo-text)] outline-none focus:border-[var(--valo-yellow)] text-sm"
                      >
                        <option value="">Select contact for quick send/schedule...</option>
                        {contacts.map(c => (
                          <option key={c.id} value={c.id}>{c.name} — {c.company} ({c.email})</option>
                        ))}
                      </select>
                      {selectedTemplateContact && (
                        <span className="text-xs text-[var(--valo-yellow)] font-bold">
                          ✓ Ready for quick actions
                        </span>
                      )}
                    </div>
                  </div>

                  {templates.filter(t => !t.is_followup).length === 0 ? (
                    <div className="tech-border p-12 text-center">
                      <div className="text-5xl mb-4">📝</div>
                      <div className="text-xl text-[var(--valo-text)] mb-2">NO TEMPLATES AVAILABLE</div>
                      <div className="text-[var(--valo-text-dim)]">Templates will appear here once created</div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
                      {templates.filter(t => !t.is_followup).map((template, i) => (
                        <motion.div
                          key={template.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: Math.min(i * 0.05, 0.3) }}
                          className="tech-border p-5 bg-[var(--valo-dark)]/30 border-l-4 border-l-[var(--valo-yellow)] hover:bg-[var(--valo-dark)]/50 transition-colors"
                        >
                          <div className="mb-3">
                            <h3 className="font-bold text-[var(--valo-text)] text-lg mb-1">{template.name}</h3>
                            <p className="text-sm text-[var(--valo-yellow)] font-mono mb-2">{template.subject}</p>
                            {template.persona_type && (
                              <span className="px-2 py-0.5 text-[10px] font-bold tracking-wide border border-[var(--valo-yellow)]/30 text-[var(--valo-yellow)]">
                                {personaLabel(template.persona_type)}
                              </span>
                            )}
                          </div>
                          
                          <div className="flex flex-col gap-2">
                            {selectedTemplateContact ? (
                              <>
                                <button
                                  onClick={() => handleTemplateQuickAction(template.id, 'send')}
                                  className="w-full bg-[var(--valo-green)]/20 border border-[var(--valo-green)]/50 text-[var(--valo-green)] px-3 py-2 text-xs font-bold tracking-wider hover:bg-[var(--valo-green)]/30 transition"
                                >
                                  ⚡ QUICK SEND
                                </button>
                                <button
                                  onClick={() => handleTemplateQuickAction(template.id, 'schedule')}
                                  className="w-full bg-[var(--valo-yellow)]/20 border border-[var(--valo-yellow)]/50 text-[var(--valo-yellow)] px-3 py-2 text-xs font-bold tracking-wider hover:bg-[var(--valo-yellow)]/30 transition"
                                >
                                  📅 QUICK SCHEDULE
                                </button>
                                <button
                                  onClick={() => handleTemplateQuickAction(template.id, 'compose')}
                                  className="w-full bg-[var(--valo-purple)]/20 border border-[var(--valo-purple)]/50 text-[var(--valo-purple)] px-3 py-2 text-xs font-bold tracking-wider hover:bg-[var(--valo-purple)]/30 transition"
                                >
                                  ✏️ EDIT & SEND
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => {
                                    if (contacts.length > 0) {
                                      setSelectedTemplateContact(contacts[0].id);
                                      setTimeout(() => handleTemplateQuickAction(template.id, 'compose'), 100);
                                    } else {
                                      notify('Add a contact first', 'error');
                                    }
                                  }}
                                  className="w-full bg-[var(--valo-purple)]/20 border border-[var(--valo-purple)]/50 text-[var(--valo-purple)] px-3 py-2 text-xs font-bold tracking-wider hover:bg-[var(--valo-purple)]/30 transition"
                                >
                                  APPLY TO COMPOSE
                                </button>
                                <button
                                  onClick={() => {
                                    setComposeTemplateId(template.id);
                                    setActiveTab('compose');
                                    notify('Template selected - choose contact in compose tab');
                                  }}
                                  className="w-full bg-[var(--valo-gray-light)]/20 border border-[var(--valo-gray-light)]/50 text-[var(--valo-text-dim)] px-3 py-2 text-xs font-bold tracking-wider hover:bg-[var(--valo-gray-light)]/30 transition"
                                >
                                  SELECT FOR COMPOSE
                                </button>
                              </>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}

                  {/* Follow-up Templates Section */}
                  {templates.filter(t => t.is_followup).length > 0 && (
                    <div className="mt-8">
                      <h3 className="text-lg font-bold text-[var(--valo-text)] mb-4 tracking-wider">FOLLOW-UP TEMPLATES</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {templates.filter(t => t.is_followup).map((template, i) => (
                          <motion.div
                            key={template.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: Math.min(i * 0.05, 0.3) }}
                            className="tech-border p-4 bg-[var(--valo-dark)]/20 border border-[var(--valo-text-dim)]/30"
                          >
                            <div className="mb-2">
                              <h4 className="font-bold text-[var(--valo-text)] text-sm">{template.name}</h4>
                              <p className="text-xs text-[var(--valo-text-dim)]">Day {template.followup_day} Follow-up</p>
                            </div>
                            <button
                              onClick={() => handleApplyTemplate(template.id)}
                              className="w-full bg-[var(--valo-purple)]/20 border border-[var(--valo-purple)]/50 text-[var(--valo-purple)] px-3 py-1.5 text-xs font-bold tracking-wider hover:bg-[var(--valo-purple)]/30 transition"
                            >
                              APPLY
                            </button>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ==================== COMPOSE TAB ==================== */}
              {activeTab === 'compose' && (
                <div className="max-w-3xl">
                  <div className="tech-border p-6 bg-[var(--valo-dark)]/30">
                    <h2 className="font-display text-xl font-bold tracking-wider text-[var(--valo-text)] mb-6 flex items-center gap-2">
                      <span className="w-2 h-2 bg-[var(--valo-purple)] rounded-full" />
                      {bulkComposeMode ? `BULK EMAIL (${selectedContacts.size} contacts)` : editingEmailId ? 'EDIT EMAIL' : 'COMPOSE NEW EMAIL'}
                    </h2>

                    {/* Bulk mode indicator */}
                    {bulkComposeMode && (
                      <div className="mb-4 p-3 bg-[var(--valo-purple)]/10 border border-[var(--valo-purple)]/30">
                        <div className="text-sm text-[var(--valo-purple)] font-bold mb-2">SENDING TO {selectedContacts.size} CONTACTS:</div>
                        <div className="flex flex-wrap gap-2">
                          {contacts.filter(c => selectedContacts.has(c.id)).map(c => (
                            <span key={c.id} className="text-xs bg-[var(--valo-dark)] px-2 py-1 border border-[var(--valo-purple)]/30">
                              {c.name} ({c.company})
                            </span>
                          ))}
                        </div>
                        <button
                          onClick={() => { setBulkComposeMode(false); setSelectedContacts(new Set()); }}
                          className="mt-2 text-xs text-[var(--valo-text-dim)] hover:text-white"
                        >
                          Cancel bulk mode
                        </button>
                      </div>
                    )}

                    {/* Contact selector */}
                    {!bulkComposeMode && (
                      <div className="mb-4">
                        <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1.5">TO: *</label>
                        <div className="flex gap-2">
                          <select
                            value={composeContactId}
                            onChange={e => setComposeContactId(e.target.value)}
                            className="flex-1 bg-black/30 border border-[var(--valo-gray)] px-3 py-2.5 text-[var(--valo-text)] outline-none focus:border-[var(--valo-purple)] text-sm"
                          >
                            <option value="">Select contact...</option>
                            {contacts.map(c => (
                              <option key={c.id} value={c.id}>{c.name} &mdash; {c.company} ({c.email})</option>
                            ))}
                          </select>
                          <button
                            onClick={() => setShowAddContact(true)}
                            className="bg-[var(--valo-cyan)]/20 border border-[var(--valo-cyan)]/50 text-[var(--valo-cyan)] px-3 text-sm font-bold hover:bg-[var(--valo-cyan)]/30 transition"
                          >
                            + NEW
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Job selector */}
                    <div className="mb-4">
                      <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1.5">RE: JOB (OPTIONAL)</label>
                      <select
                        value={composeJobId}
                        onChange={e => setComposeJobId(e.target.value)}
                        className="w-full bg-black/30 border border-[var(--valo-gray)] px-3 py-2.5 text-[var(--valo-text)] outline-none focus:border-[var(--valo-purple)] text-sm"
                      >
                        <option value="">No job linked</option>
                        {jobs.map(j => (
                          <option key={j.id} value={j.id}>{j.title} @ {j.company}</option>
                        ))}
                      </select>
                    </div>

                    {/* Template selector with quick access */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-1.5">
                        <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest">TEMPLATE</label>
                        <button
                          onClick={() => setActiveTab('templates')}
                          className="text-xs text-[var(--valo-yellow)] hover:brightness-125 font-bold tracking-wider"
                        >
                          📋 BROWSE ALL →
                        </button>
                      </div>
                      <div className="flex gap-2">
                        <select
                          value={composeTemplateId}
                          onChange={e => handleTemplateChange(e.target.value)}
                          className="flex-1 bg-black/30 border border-[var(--valo-gray)] px-3 py-2.5 text-[var(--valo-text)] outline-none focus:border-[var(--valo-purple)] text-sm"
                        >
                          <option value="">Write from scratch</option>
                          {templates.filter(t => !t.is_followup).map(t => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                          ))}
                        </select>
                        {composeTemplateId && (
                          <button
                            onClick={() => {
                              const template = templates.find(t => t.id === composeTemplateId);
                              if (template) {
                                setTemplatePreview({ templateId: template.id, subject: template.subject, body: '' });
                              }
                            }}
                            className="bg-[var(--valo-yellow)]/20 border border-[var(--valo-yellow)]/50 text-[var(--valo-yellow)] px-3 text-sm font-bold hover:bg-[var(--valo-yellow)]/30 transition"
                            title="Preview template"
                          >
                            👁️
                          </button>
                        )}
                      </div>
                      {/* Quick template buttons */}
                      {templates.filter(t => !t.is_followup).length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {templates.filter(t => !t.is_followup).slice(0, 3).map(t => (
                            <button
                              key={t.id}
                              onClick={() => {
                                if (!composeContactId) {
                                  notify('Select a contact first to apply template', 'error');
                                  return;
                                }
                                handleTemplateChange(t.id);
                              }}
                              className={`px-3 py-1 text-xs font-bold tracking-wider transition ${
                                composeTemplateId === t.id
                                  ? 'bg-[var(--valo-yellow)] text-black'
                                  : 'bg-[var(--valo-dark)]/50 border border-[var(--valo-gray)] text-[var(--valo-text-dim)] hover:text-[var(--valo-yellow)]'
                              }`}
                            >
                              {t.name}
                            </button>
                          ))}
                          {templates.filter(t => !t.is_followup).length > 3 && (
                            <button
                              onClick={() => setActiveTab('templates')}
                              className="px-3 py-1 text-xs font-bold tracking-wider bg-[var(--valo-dark)]/50 border border-[var(--valo-gray)] text-[var(--valo-text-dim)] hover:text-[var(--valo-yellow)]"
                            >
                              +{templates.filter(t => !t.is_followup).length - 3} more
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="border-t border-[var(--valo-gray)] pt-4 mb-4">
                      {/* Subject */}
                      <div className="mb-4">
                        <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1.5">SUBJECT</label>
                        <input
                          type="text"
                          value={composeSubject}
                          onChange={e => setComposeSubject(e.target.value)}
                          placeholder="Email subject line..."
                          className="w-full bg-black/30 border border-[var(--valo-gray)] px-3 py-2.5 text-[var(--valo-text)] outline-none focus:border-[var(--valo-purple)] text-sm"
                        />
                      </div>

                      {/* Body */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-1.5">
                          <label className="text-xs text-[var(--valo-text-dim)] tracking-widest">BODY</label>
                          <button
                            onClick={() => setShowPreview(!showPreview)}
                            className="text-xs text-[var(--valo-purple)] hover:brightness-125 tracking-wider font-bold transition"
                          >
                            {showPreview ? '\u2190 EDIT' : 'PREVIEW \u2192'}
                          </button>
                        </div>
                        {showPreview ? (
                          <div className="bg-white/5 border border-[var(--valo-gray)] p-4 min-h-[300px] whitespace-pre-wrap text-sm text-[var(--valo-text)] leading-relaxed">
                            {composeBody || <span className="text-[var(--valo-text-dim)] italic">Nothing to preview yet</span>}
                          </div>
                        ) : (
                          <textarea
                            value={composeBody}
                            onChange={e => setComposeBody(e.target.value)}
                            placeholder="Write your email here..."
                            rows={14}
                            className="w-full bg-black/30 border border-[var(--valo-gray)] px-3 py-2.5 text-[var(--valo-text)] outline-none focus:border-[var(--valo-purple)] text-sm resize-y leading-relaxed"
                          />
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 justify-end flex-wrap">
                      {editingEmailId && (
                        <button
                          onClick={resetCompose}
                          className="text-[var(--valo-text-dim)] hover:text-white px-4 py-2.5 font-bold text-sm tracking-wider transition"
                        >
                          CANCEL
                        </button>
                      )}
                      {bulkComposeMode ? (
                        <>
                          <button
                            onClick={() => { setBulkComposeMode(false); setSelectedContacts(new Set()); resetCompose(); }}
                            className="text-[var(--valo-text-dim)] hover:text-white px-4 py-2.5 font-bold text-sm tracking-wider transition"
                          >
                            CANCEL
                          </button>
                          <button
                            onClick={handleBulkSend}
                            className="bg-[var(--valo-red)] text-white px-6 py-2.5 font-bold text-sm tracking-wider hover:brightness-110 transition"
                            style={{ clipPath: 'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)' }}
                          >
                            SEND TO ALL ({selectedContacts.size})
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={handleSaveDraft}
                            className="bg-[var(--valo-gray-light)] text-[var(--valo-text)] px-6 py-2.5 font-bold text-sm tracking-wider hover:brightness-125 transition"
                            style={{ clipPath: 'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)' }}
                          >
                            SAVE DRAFT
                          </button>
                          <button
                            onClick={handleScheduleFromCompose}
                            className="bg-[var(--valo-yellow)]/90 text-black px-6 py-2.5 font-bold text-sm tracking-wider hover:brightness-110 transition"
                            style={{ clipPath: 'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)' }}
                          >
                            SCHEDULE
                          </button>
                          <button
                            onClick={handleSendNow}
                            className="bg-[var(--valo-red)] text-white px-6 py-2.5 font-bold text-sm tracking-wider hover:brightness-110 transition"
                            style={{ clipPath: 'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)' }}
                          >
                            SEND NOW
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* ==================== OUTBOX TAB ==================== */}
              {activeTab === 'outbox' && (
                <div>
                  {/* Status filters */}
                  <div className="flex gap-2 mb-4 flex-wrap">
                    {['all', 'draft', 'scheduled', 'sent', 'failed'].map(status => (
                      <button
                        key={status}
                        onClick={() => setEmailStatusFilter(status)}
                        className={`px-4 py-1.5 text-xs font-bold tracking-widest uppercase transition tech-button ${
                          emailStatusFilter === status
                            ? 'bg-[var(--valo-red)]/20 border-[var(--valo-red)] text-[var(--valo-red)]'
                            : 'text-[var(--valo-text-dim)] border-[var(--valo-gray-light)]'
                        }`}
                      >
                        {status}
                      </button>
                    ))}
                  </div>

                  {emails.length === 0 ? (
                    <div className="tech-border p-12 text-center">
                      <div className="text-5xl mb-4">&#9993;&#65039;</div>
                      <div className="text-xl text-[var(--valo-text)] mb-2">NO EMAILS IN OUTBOX</div>
                      <div className="text-[var(--valo-text-dim)] mb-6">Compose an email from the Compose tab</div>
                      <button
                        onClick={() => setActiveTab('compose')}
                        className="bg-[var(--valo-purple)] text-white px-8 py-3 font-bold tracking-wider hover:brightness-110"
                      >
                        START COMPOSING
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3 pb-8">
                      <AnimatePresence mode="popLayout">
                        {emails.map((email, i) => (
                          <motion.div
                            key={email.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ delay: Math.min(i * 0.03, 0.3) }}
                            className="tech-border p-5 bg-[var(--valo-dark)]/30 hover:bg-[var(--valo-dark)]/50 transition-colors"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex-1 min-w-0">
                                <h3 className="font-bold text-[var(--valo-text)] text-lg truncate">{email.subject || '(No subject)'}</h3>
                                <p className="text-sm text-[var(--valo-cyan)]">
                                  To: {email.contact_name} <span className="text-[var(--valo-text-dim)] font-mono">({email.contact_email})</span>
                                </p>
                              </div>
                              <span className={`px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border ml-3 whitespace-nowrap ${statusStyle(email.status)}`}>
                                {email.status}
                              </span>
                            </div>
                            <p className="text-[var(--valo-text-dim)] text-sm mb-3 line-clamp-2 leading-relaxed">
                              {email.body}
                            </p>

                            <div className="flex justify-between items-center flex-wrap gap-2">
                              <div className="text-xs text-[var(--valo-text-dim)] font-mono space-x-4">
                                {email.scheduled_at && (
                                  <span>Scheduled: {new Date(email.scheduled_at).toLocaleString()}</span>
                                )}
                                {email.sent_at && (
                                  <span>Sent: {new Date(email.sent_at).toLocaleString()}</span>
                                )}
                                {!email.scheduled_at && !email.sent_at && email.created_at && (
                                  <span>Created: {new Date(email.created_at).toLocaleDateString()}</span>
                                )}
                                {email.error_message && (
                                  <span className="text-[var(--valo-red)]">Error: {email.error_message}</span>
                                )}
                              </div>
                              <div className="flex gap-2 items-center flex-wrap">
                                {email.status === 'draft' && (
                                  <>
                                    <button
                                      onClick={async () => {
                                        await api.sendEmailNow(email.id);
                                        notify('EMAIL DISPATCHED');
                                        fetchEmails();
                                      }}
                                      className="bg-[var(--valo-green)]/20 border border-[var(--valo-green)]/50 text-[var(--valo-green)] px-3 py-1 text-xs font-bold tracking-wider hover:bg-[var(--valo-green)]/30 transition"
                                    >
                                      ⚡ SEND
                                    </button>
                                    <button
                                      onClick={() => handleScheduleAuto(email.id)}
                                      className="bg-[var(--valo-yellow)]/20 border border-[var(--valo-yellow)]/50 text-[var(--valo-yellow)] px-3 py-1 text-xs font-bold tracking-wider hover:bg-[var(--valo-yellow)]/30 transition"
                                    >
                                      SCHEDULE
                                    </button>
                                    <button
                                      onClick={() => handleEditEmail(email)}
                                      className="bg-[var(--valo-purple)]/20 border border-[var(--valo-purple)]/50 text-[var(--valo-purple)] px-3 py-1 text-xs font-bold tracking-wider hover:bg-[var(--valo-purple)]/30 transition"
                                    >
                                      EDIT
                                    </button>
                                  </>
                                )}
                                {email.status === 'scheduled' && (
                                  <button
                                    onClick={() => {
                                      setScheduleEmailId(email.id);
                                      setScheduleTime(email.scheduled_at || '');
                                      setShowScheduleModal(true);
                                    }}
                                    className="bg-[var(--valo-yellow)]/20 border border-[var(--valo-yellow)]/50 text-[var(--valo-yellow)] px-3 py-1 text-xs font-bold tracking-wider hover:bg-[var(--valo-yellow)]/30 transition"
                                  >
                                    RESCHEDULE
                                  </button>
                                )}
                                <button
                                  onClick={() => setPreviewEmail(email)}
                                  className="text-xs text-[var(--valo-text-dim)] hover:text-[var(--valo-cyan)] font-bold tracking-wider transition px-2 py-1"
                                >
                                  VIEW
                                </button>
                                {(email.status === 'draft' || email.status === 'scheduled') && (
                                  <button
                                    onClick={() => setConfirmDelete({ type: 'email', id: email.id })}
                                    className="text-xs text-[var(--valo-red)] hover:brightness-125 font-bold tracking-wider transition px-2 py-1"
                                  >
                                    DELETE
                                  </button>
                                )}
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </main>

        {/* ==================== MODALS ==================== */}

        {/* Add Contact Modal */}
        {showAddContact && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={() => setShowAddContact(false)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--valo-dark)] border border-[var(--valo-cyan)] p-8 max-w-lg w-full tech-border shadow-[0_0_50px_rgba(34,211,238,0.15)]"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="font-display text-2xl font-bold text-[var(--valo-text)] mb-6 tracking-wider">REGISTER NEW CONTACT</h2>
              <div className="space-y-3 mb-6">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">NAME *</label>
                    <input type="text" value={contactForm.name} onChange={e => setContactForm({ ...contactForm, name: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">EMAIL *</label>
                    <input type="email" value={contactForm.email} onChange={e => setContactForm({ ...contactForm, email: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm font-mono" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">TITLE</label>
                    <input type="text" placeholder="e.g. Senior Recruiter" value={contactForm.title} onChange={e => setContactForm({ ...contactForm, title: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">COMPANY *</label>
                    <input type="text" value={contactForm.company} onChange={e => setContactForm({ ...contactForm, company: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">PERSONA</label>
                    <select value={contactForm.persona} onChange={e => setContactForm({ ...contactForm, persona: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm">
                      <option value="unknown">Other</option>
                      <option value="recruiter">Recruiter</option>
                      <option value="hiring_manager">Hiring Manager</option>
                      <option value="engineering_manager">Engineering Manager</option>
                      <option value="hr">HR</option>
                      <option value="talent_acquisition">Talent Acquisition</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">LINK TO JOB</label>
                    <select value={contactForm.job_id} onChange={e => setContactForm({ ...contactForm, job_id: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm">
                      <option value="">None</option>
                      {jobs.map(j => <option key={j.id} value={j.id}>{j.title} @ {j.company}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">LINKEDIN URL</label>
                  <input type="url" placeholder="https://linkedin.com/in/..." value={contactForm.linkedin_url} onChange={e => setContactForm({ ...contactForm, linkedin_url: e.target.value })} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm font-mono" />
                </div>
                <div>
                  <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-1">NOTES</label>
                  <textarea placeholder="Any additional notes..." value={contactForm.notes} onChange={e => setContactForm({ ...contactForm, notes: e.target.value })} rows={2} className="w-full bg-black/30 border border-[var(--valo-gray)] p-2.5 text-white outline-none focus:border-[var(--valo-cyan)] text-sm resize-none" />
                </div>
              </div>
              <div className="flex justify-end gap-4">
                <button onClick={() => setShowAddContact(false)} className="text-[var(--valo-text-dim)] hover:text-white font-bold tracking-wider text-sm">CANCEL</button>
                <button onClick={handleAddContact} className="bg-[var(--valo-cyan)] text-black px-8 py-2.5 font-bold tracking-wider text-sm hover:brightness-110 transition">REGISTER</button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Find Contacts Modal */}
        {showFindContacts && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={() => setShowFindContacts(false)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--valo-dark)] border border-[var(--valo-cyan)] p-8 max-w-lg w-full tech-border shadow-[0_0_50px_rgba(34,211,238,0.15)]"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="font-display text-2xl font-bold text-[var(--valo-text)] mb-6 tracking-wider">FIND CONTACTS</h2>
              
              {/* Mode Toggle */}
              <div className="flex gap-2 mb-6">
                <button
                  onClick={() => { setFindContactsMode('company'); setFindContactsJobId(''); }}
                  className={`flex-1 px-4 py-2 font-bold text-sm tracking-wider transition ${
                    findContactsMode === 'company'
                      ? 'bg-[var(--valo-cyan)] text-black'
                      : 'bg-black/30 border border-[var(--valo-gray)] text-[var(--valo-text-dim)] hover:text-white'
                  }`}
                >
                  BY COMPANY
                </button>
                <button
                  onClick={() => { setFindContactsMode('job'); setFindContactsCompany(''); }}
                  className={`flex-1 px-4 py-2 font-bold text-sm tracking-wider transition ${
                    findContactsMode === 'job'
                      ? 'bg-[var(--valo-cyan)] text-black'
                      : 'bg-black/30 border border-[var(--valo-gray)] text-[var(--valo-text-dim)] hover:text-white'
                  }`}
                >
                  BY JOB
                </button>
              </div>

              {/* Company Mode */}
              {findContactsMode === 'company' && (
                <div className="mb-6">
                  <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-2">COMPANY NAME</label>
                  <input
                    type="text"
                    placeholder="e.g. Google, Microsoft, Stripe..."
                    value={findContactsCompany}
                    onChange={e => setFindContactsCompany(e.target.value)}
                    className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none focus:border-[var(--valo-cyan)] text-sm"
                    autoFocus
                  />
                  <p className="text-xs text-[var(--valo-text-dim)] mt-2">
                    Searches Apollo.io for recruiters, hiring managers, and engineering managers at this company
                  </p>
                </div>
              )}

              {/* Job Mode */}
              {findContactsMode === 'job' && (
                <div className="mb-6">
                  <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-2">SELECT JOB</label>
                  <select
                    value={findContactsJobId}
                    onChange={e => setFindContactsJobId(e.target.value)}
                    className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none focus:border-[var(--valo-cyan)] text-sm"
                  >
                    <option value="">Select a job...</option>
                    {jobs.map(j => (
                      <option key={j.id} value={j.id}>
                        {j.title} @ {j.company} {j.status === 'applied' ? '(Applied)' : ''}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-[var(--valo-text-dim)] mt-2">
                    Finds contacts at the company for this job and links them automatically
                  </p>
                </div>
              )}

              {/* Info Box */}
              <div className="bg-[var(--valo-cyan)]/10 border border-[var(--valo-cyan)]/30 p-4 mb-6">
                <div className="text-xs text-[var(--valo-cyan)] font-bold tracking-wider mb-1">APOLLO.IO INTEGRATION</div>
                <div className="text-xs text-[var(--valo-text-dim)] leading-relaxed">
                  Requires APOLLO_API_KEY in .env. Get your API key from{' '}
                  <a href="https://app.apollo.io/#/settings/integrations/api" target="_blank" rel="noopener noreferrer" className="text-[var(--valo-cyan)] hover:underline">
                    Apollo Settings
                  </a>
                </div>
              </div>

              <div className="flex justify-end gap-4">
                <button
                  onClick={() => {
                    setShowFindContacts(false);
                    setFindContactsCompany('');
                    setFindContactsJobId('');
                  }}
                  className="text-[var(--valo-text-dim)] hover:text-white font-bold tracking-wider text-sm"
                >
                  CANCEL
                </button>
                <button
                  onClick={handleFindContacts}
                  disabled={isScraping}
                  className="bg-[var(--valo-cyan)] text-black px-8 py-2.5 font-bold tracking-wider text-sm hover:brightness-110 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isScraping ? 'SCANNING...' : 'DEPLOY SCANNET'}
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Email Preview Modal */}
        {previewEmail && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={() => setPreviewEmail(null)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--valo-dark)] border border-[var(--valo-gray-light)] p-8 max-w-2xl w-full tech-border max-h-[80vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <span className={`px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border mb-2 inline-block ${statusStyle(previewEmail.status)}`}>{previewEmail.status}</span>
                  <h2 className="font-display text-2xl font-bold text-[var(--valo-text)] tracking-wider">{previewEmail.subject}</h2>
                </div>
                <button onClick={() => setPreviewEmail(null)} className="text-[var(--valo-text-dim)] hover:text-white flex-shrink-0 ml-4">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
              <div className="space-y-2 mb-6 text-sm border-b border-[var(--valo-gray)] pb-4">
                <div><span className="text-[var(--valo-text-dim)]">To:</span> <span className="text-[var(--valo-cyan)]">{previewEmail.contact_name}</span> <span className="font-mono text-[var(--valo-text-dim)]">&lt;{previewEmail.contact_email}&gt;</span></div>
                {previewEmail.contact_company && <div><span className="text-[var(--valo-text-dim)]">Company:</span> <span className="text-[var(--valo-text)]">{previewEmail.contact_company}</span></div>}
                {previewEmail.scheduled_at && <div><span className="text-[var(--valo-text-dim)]">Scheduled:</span> <span className="text-[var(--valo-yellow)]">{new Date(previewEmail.scheduled_at).toLocaleString()}</span></div>}
                {previewEmail.sent_at && <div><span className="text-[var(--valo-text-dim)]">Sent:</span> <span className="text-[var(--valo-green)]">{new Date(previewEmail.sent_at).toLocaleString()}</span></div>}
              </div>
              <div className="whitespace-pre-wrap text-[var(--valo-text)] leading-relaxed text-sm bg-white/5 p-6 border border-[var(--valo-gray)]">
                {previewEmail.body}
              </div>
              {previewEmail.status === 'draft' && (
                <div className="flex gap-3 justify-end mt-6">
                  <button onClick={() => { handleEditEmail(previewEmail); setPreviewEmail(null); }} className="text-[var(--valo-purple)] font-bold text-sm tracking-wider hover:brightness-125">EDIT</button>
                  <button
                    onClick={async () => { await api.sendEmailNow(previewEmail.id); setPreviewEmail(null); fetchEmails(); notify('EMAIL DISPATCHED'); }}
                    className="bg-[var(--valo-red)] text-white px-6 py-2 font-bold text-sm tracking-wider hover:brightness-110"
                  >
                    SEND NOW
                  </button>
                </div>
              )}
            </motion.div>
          </div>
        )}

        {/* Schedule Modal */}
        {showScheduleModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={() => setShowScheduleModal(false)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--valo-dark)] border border-[var(--valo-yellow)] p-8 max-w-md w-full tech-border"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="font-display text-2xl font-bold text-[var(--valo-text)] mb-6 tracking-wider">SCHEDULE EMAIL</h2>
              <div className="mb-6">
                <label className="block text-xs text-[var(--valo-text-dim)] tracking-widest mb-2">SEND AT</label>
                <input
                  type="datetime-local"
                  value={scheduleTime}
                  onChange={e => setScheduleTime(e.target.value)}
                  className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none focus:border-[var(--valo-yellow)] text-sm"
                />
              </div>
              <div className="flex justify-between">
                <button
                  onClick={() => {
                    handleScheduleAuto(scheduleEmailId);
                    setShowScheduleModal(false);
                  }}
                  className="text-[var(--valo-cyan)] font-bold text-sm tracking-wider hover:brightness-125"
                >
                  USE OPTIMAL TIME
                </button>
                <div className="flex gap-4">
                  <button onClick={() => setShowScheduleModal(false)} className="text-[var(--valo-text-dim)] hover:text-white font-bold text-sm">CANCEL</button>
                  <button onClick={handleScheduleCustom} className="bg-[var(--valo-yellow)] text-black px-6 py-2 font-bold text-sm tracking-wider hover:brightness-110">CONFIRM</button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {/* Template Preview Modal */}
        {templatePreview && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={() => setTemplatePreview(null)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--valo-dark)] border border-[var(--valo-yellow)] p-8 max-w-2xl w-full tech-border shadow-[0_0_50px_rgba(255,193,7,0.15)] max-h-[80vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex justify-between items-start mb-6">
                <h2 className="font-display text-2xl font-bold text-[var(--valo-yellow)] tracking-wider">
                  TEMPLATE PREVIEW
                </h2>
                <button onClick={() => setTemplatePreview(null)} className="text-[var(--valo-text-dim)] hover:text-white flex-shrink-0 ml-4">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-[var(--valo-text-dim)] tracking-widest mb-1 block">SUBJECT</label>
                  <div className="bg-black/30 border border-[var(--valo-gray)] p-3 text-[var(--valo-text)] text-sm">
                    {templatePreview.subject}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-[var(--valo-text-dim)] tracking-widest mb-1 block">BODY</label>
                  <div className="bg-black/30 border border-[var(--valo-gray)] p-4 text-[var(--valo-text)] text-sm whitespace-pre-wrap leading-relaxed min-h-[200px]">
                    {templatePreview.body || 'Template body will be rendered when applied to a contact'}
                  </div>
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-[var(--valo-gray)]">
                  <button
                    onClick={() => {
                      handleApplyTemplate(templatePreview.templateId);
                      setTemplatePreview(null);
                    }}
                    className="bg-[var(--valo-yellow)] text-black px-6 py-2 font-bold text-sm tracking-wider hover:brightness-110"
                  >
                    APPLY TO COMPOSE
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {/* Confirm Delete Modal */}
        {confirmDelete && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={() => setConfirmDelete(null)}>
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[var(--valo-dark)] border border-[var(--valo-red)] p-8 max-w-sm w-full tech-border"
              onClick={e => e.stopPropagation()}
            >
              <h2 className="font-display text-xl font-bold text-[var(--valo-red)] mb-4 tracking-wider">CONFIRM DELETE</h2>
              <p className="text-[var(--valo-text-dim)] mb-6">Are you sure you want to delete this {confirmDelete.type}? This action cannot be undone.</p>
              <div className="flex justify-end gap-4">
                <button onClick={() => setConfirmDelete(null)} className="text-[var(--valo-text-dim)] hover:text-white font-bold text-sm">CANCEL</button>
                <button onClick={handleDeleteConfirm} className="bg-[var(--valo-red)] text-white px-6 py-2 font-bold text-sm tracking-wider hover:brightness-110">DELETE</button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Toast */}
        <AnimatePresence>
          {toast.show && (
            <motion.div
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 20, opacity: 0 }}
              className={`fixed bottom-10 left-1/2 -translate-x-1/2 font-bold px-8 py-3 z-[300] shadow-lg ${
                toast.type === 'error' ? 'bg-[var(--valo-red)] text-white' : 'bg-[var(--valo-cyan)] text-black'
              }`}
              style={{ clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' }}
            >
              {toast.message}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
