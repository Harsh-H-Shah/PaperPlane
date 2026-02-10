const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export interface Profile {
  agent_name: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  linkedin?: string;
  github?: string;
  avatar?: string;
  valorant_agent?: string;
}

export interface Gamification {
  total_xp: number;
  level: number;
  level_title: string;
  current_xp_in_level: number;
  xp_for_next_level: number;
  streak: number;
  applications_today: number;
  rank_icon?: string;
}

export interface Stats {
  total: number;
  applied: number;
  pending: number;
  failed: number;
  by_source: Record<string, number>;
  recent_applications: Array<{
    id: string;
    title: string;
    company: string;
    applied_at: string | null;
  }>;
  weekly_activity?: { day: string; applications: number }[];
}

export interface Quest {
  id: string;
  name: string;
  description: string;
  type: 'daily' | 'weekly' | 'achievement';
  target: number;
  progress: number;
  xp_reward: number;
  completed: boolean;
  priority: boolean;
}

export interface CombatHistoryItem {
  id: string;
  title: string;
  company: string;
  source: string;
  status: string;
  status_label: string;
  status_color: string;
  xp_reward: number;
  icon: string;
  applied_at: string | null;
  discovered_at: string | null;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  status: string;
  source: string;
  application_type: string;
  apply_url?: string;
  discovered_at: string | null;
  posted_date?: string | null;
}

export interface Contact {
  id: string;
  name: string;
  email: string;
  title: string;
  company: string;
  linkedin_url?: string;
  persona: string;
  source: string;
  job_id?: string;
  notes?: string;
  created_at: string;
}

export interface Email {
  id: string;
  contact_id: string;
  contact_name: string;
  contact_email: string;
  contact_company: string;
  job_id: string | null;
  template_id: string | null;
  subject: string;
  body: string;
  status: string;
  scheduled_at: string | null;
  sent_at: string | null;
  followup_number: number;
  created_at: string;
  error_message: string | null;
}

export interface Template {
  id: string;
  name: string;
  subject: string;
  body?: string;
  persona_type: string | null;
  is_followup: boolean;
  followup_day: number;
}

export interface EmailStats {
  total_emails: number;
  sent: number;
  opened: number;
  replied: number;
  scheduled: number;
  open_rate: number;
  reply_rate: number;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('paperplane_admin_token') : null;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  
  return res.json();
}

export const api = {
  // ==================== Profile ====================
  getProfile: () => fetchApi<Profile>('/api/profile'),
  
  getGamification: () => fetchApi<Gamification>('/api/gamification'),
  
  getStats: () => fetchApi<Stats>('/api/stats'),
  
  getQuests: () => fetchApi<{ quests: Quest[] }>('/api/quests'),
  
  getCombatHistory: () => fetchApi<{ history: CombatHistoryItem[] }>('/api/combat-history'),

  updateProfile: (data: { valorant_agent?: string }) =>
    fetchApi<{ success: boolean; valorant_agent: string }>('/api/profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // ==================== Jobs ====================
  getJobs: (params?: {
    status?: string;
    source?: string;
    type?: string;
    search?: string;
    sort?: string;
    page?: number;
    per_page?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.source) searchParams.set('source', params.source);
    if (params?.type) searchParams.set('type', params.type);
    if (params?.search) searchParams.set('search', params.search);
    if (params?.sort) searchParams.set('sort', params.sort);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.per_page) searchParams.set('per_page', params.per_page.toString());
    
    const query = searchParams.toString();
    return fetchApi<{
      total: number;
      page: number;
      per_page: number;
      total_pages: number;
      has_more: boolean;
      jobs: Job[];
    }>(`/api/jobs${query ? `?${query}` : ''}`);
  },

  createJob: (data: { 
    title: string; 
    company: string; 
    url: string; 
    location?: string;
    application_type?: string;
  }) =>
    fetchApi<{ id: string; success: boolean; job?: Job }>('/api/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateJob: (jobId: string, data: { status: string }) =>
    fetchApi<{ success: boolean }>(`/api/jobs/${jobId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
    
  deleteJob: (jobId: string) =>
    fetchApi<{ success: boolean }>(`/api/jobs/${jobId}`, {
      method: 'DELETE',
    }),

  // ==================== Scraping ====================
  triggerScrape: (sources?: string[], limit?: number) =>
    fetchApi<{ status: string; message: string }>('/api/scrape', {
      method: 'POST',
      body: JSON.stringify({ sources, limit: limit || 100 }),
    }),
  
  getScrapeProgress: () =>
    fetchApi<{
      is_running: boolean;
      current_source: string;
      jobs_found: number;
      jobs_new: number;
      last_updated: string | null;
    }>('/api/scrape/progress'),

  // ==================== Apply ====================
  triggerRun: () =>
    fetchApi<{ status: string; message: string }>('/api/run', {
      method: 'POST',
    }),

  triggerApply: (jobId: string) =>
    fetchApi<{ status: string; job_id: string; message: string }>(`/api/apply/${jobId}`, {
      method: 'POST',
    }),

  getApplyStatus: (jobId: string) =>
    fetchApi<{ is_running: boolean; job_id: string; status: string }>(`/api/apply/${jobId}/status`),

  abortApply: (jobId: string) =>
    fetchApi<{ status: string; message: string }>(`/api/apply/${jobId}/abort`, {
      method: 'POST',
    }),

  // ==================== Contacts ====================
  getContacts: (params?: { company?: string; search?: string; persona?: string; job_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.company) searchParams.set('company', params.company);
    if (params?.search) searchParams.set('search', params.search);
    if (params?.persona) searchParams.set('persona', params.persona);
    if (params?.job_id) searchParams.set('job_id', params.job_id);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    const query = searchParams.toString();
    return fetchApi<{ total: number; contacts: Contact[] }>(`/api/contacts${query ? `?${query}` : ''}`);
  },

  createContact: (data: { name: string; email: string; title?: string; company: string; persona?: string; linkedin_url?: string; job_id?: string; notes?: string }) =>
    fetchApi<{ id: string; success: boolean }>('/api/contacts', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateContact: (contactId: string, data: Partial<Contact>) =>
    fetchApi<{ success: boolean }>(`/api/contacts/${contactId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteContact: (contactId: string) =>
    fetchApi<{ success: boolean }>(`/api/contacts/${contactId}`, {
      method: 'DELETE',
    }),

  scrapeContacts: (params: { company?: string; job_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params.company) searchParams.set('company', params.company);
    if (params.job_id) searchParams.set('job_id', params.job_id);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    return fetchApi<{ status: string; message: string }>(
      `/api/contacts/scrape?${searchParams.toString()}`,
      { method: 'POST' }
    );
  },

  // ==================== Emails ====================
  getEmails: (params?: { status?: string; search?: string; job_id?: string; contact_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.search) searchParams.set('search', params.search);
    if (params?.job_id) searchParams.set('job_id', params.job_id);
    if (params?.contact_id) searchParams.set('contact_id', params.contact_id);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    const query = searchParams.toString();
    return fetchApi<{ total: number; emails: Email[] }>(`/api/emails${query ? `?${query}` : ''}`);
  },

  createEmail: (data: { contact_id: string; job_id?: string; template_id?: string; subject: string; body: string }) =>
    fetchApi<{ id: string; success: boolean }>('/api/emails', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  renderEmail: (data: { contact_id: string; job_id?: string; template_id?: string }) =>
    fetchApi<{ subject: string; body: string; template_name: string | null }>('/api/emails/render', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateEmail: (emailId: string, data: { subject?: string; body?: string; status?: string; scheduled_at?: string }) =>
    fetchApi<{ success: boolean }>(`/api/emails/${emailId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteEmail: (emailId: string) =>
    fetchApi<{ success: boolean }>(`/api/emails/${emailId}`, {
      method: 'DELETE',
    }),

  getEmail: (emailId: string) =>
    fetchApi<Email>(`/api/emails/${emailId}`),

  sendEmailNow: (emailId: string) =>
    fetchApi<{ status: string; email_id: string }>(`/api/emails/${emailId}/send`, {
      method: 'POST',
    }),
    
  scheduleEmail: (emailId: string) =>
    fetchApi<{ success: boolean; scheduled_at: string }>(`/api/emails/${emailId}/schedule`, {
      method: 'POST',
    }),

  // ==================== Templates ====================
  getTemplates: () => fetchApi<{ total: number; templates: Template[] }>('/api/templates'),
  
  getTemplate: (templateId: string) => fetchApi<Template>(`/api/templates/${templateId}`),

  // ==================== Campaigns ====================
  createCampaign: (data: { job_id: string; max_contacts: number; personas?: string[] }) =>
    fetchApi<{ status: string; job_id: string }>('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ==================== Email Stats ====================
  getEmailStats: () => fetchApi<EmailStats>('/api/email-stats'),

  processScheduledEmails: () =>
    fetchApi<{ status: string; message: string }>('/api/emails/process', {
      method: 'POST',
    }),
};
