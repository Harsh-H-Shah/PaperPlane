'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/Sidebar';
import { api, Profile, Gamification, Email, Contact } from '@/lib/api';
import ValorantDropdown from '@/components/ValorantDropdown';

export default function EmailsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [gamification, setGamification] = useState<Gamification | null>(null);
  const [emails, setEmails] = useState<Email[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'emails' | 'contacts'>('emails');
  
  // Email Filters
  const [emailFilter, setEmailFilter] = useState<string>('all');
  
  // Modals
  const [showScrapeModal, setShowScrapeModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  
  // Forms
  const [scrapeCompany, setScrapeCompany] = useState('');
  const [manualContact, setManualContact] = useState({ name: '', email: '', company: '', title: '' });
  const [campaignJobId, setCampaignJobId] = useState('');

  // Toast
  const [toastMessage, setToastMessage] = useState('');
  const [showToast, setShowToast] = useState(false);

  const showSuccess = (msg: string) => {
    setToastMessage(msg);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const fetchEmailData = async () => {
    setLoading(true);
    try {
      const emailRes = await api.getEmails({ status: emailFilter !== 'all' ? emailFilter : undefined, limit: 100 });
      setEmails(emailRes.emails);
    } catch (err) {
      console.error(err);
    } finally {
        setLoading(false);
    }
  };

  const fetchContactData = async () => {
    setLoading(true);
    try {
      const contactRes = await api.getContacts({ limit: 100 });
      setContacts(contactRes.contacts);
    } catch (err) {
        console.error(err);
    } finally {
        setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      const [p, g] = await Promise.all([api.getProfile(), api.getGamification()]);
      setProfile(p);
      setGamification(g);
    };
    init();
  }, []);

  useEffect(() => {
    if (activeTab === 'emails') fetchEmailData();
    else fetchContactData();
  }, [activeTab, emailFilter]);

  const handleScrape = async () => {
    if (!scrapeCompany) return;
    showSuccess(`DEPLOYING SATELLITE TO SCAN: ${scrapeCompany}`);
    setShowScrapeModal(false);
    try {
        await api.scrapeContacts(scrapeCompany, 10);
        await new Promise(r => setTimeout(r, 2000)); // Simulate delay
        fetchContactData();
        showSuccess(`INTEL ACQUIRED FROM ${scrapeCompany}`);
    } catch (e) {
        console.error(e);
        showSuccess('SCAN FAILED');
    }
  };

  const handleManualAdd = async () => {
      try {
          await api.createContact(manualContact);
          setShowManualModal(false);
          fetchContactData();
          showSuccess('ASSET REGISTERED');
          setManualContact({ name: '', email: '', company: '', title: '' });
      } catch (e) {
          console.error(e);
      }
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'sent': return 'text-[var(--valo-green)] border border-[var(--valo-green)] bg-[var(--valo-green)]/10';
      case 'draft': return 'status-gray';
      case 'scheduled': return 'status-yellow';
      case 'failed': return 'status-red';
      default: return 'status-gray';
    }
  };

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
        <main className="flex-1 p-8 overflow-y-auto relative">
          <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-[var(--valo-text-dim)] text-sm mb-1">
                <span className={`w-2 h-2 rounded-full ${activeTab === 'emails' ? 'bg-[var(--valo-purple)] pulse-purple' : 'bg-[var(--valo-cyan)] pulse-green'}`}></span>
                {activeTab === 'emails' ? 'COMMUNICATIONS' : 'TARGET DATABASE'}
              </div>
              <h1 className="font-display text-4xl font-bold tracking-wider text-[var(--valo-text)]">
                {activeTab === 'emails' ? 'OUTREACH LOGS' : 'CONTACT INTEL'}
              </h1>
            </div>

            <div className="flex gap-4">
                <button 
                  onClick={() => setShowScrapeModal(true)}
                  className="bg-transparent border border-[var(--valo-cyan)] text-[var(--valo-cyan)] px-6 py-3 font-bold tracking-wider text-sm tech-button hover:bg-[var(--valo-cyan)] hover:text-black transition-all"
                  style={{ clipPath: 'polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%)' }}
                >
                  FIND TARGETS
                </button>
                <button 
                  onClick={() => setShowManualModal(true)}
                  className="bg-[var(--valo-dark)] border border-[var(--valo-text-dim)] text-[var(--valo-text)] px-6 py-3 font-bold tracking-wider text-sm tech-button hover:border-[var(--valo-white)] transition-all"
                >
                  ADD MANUAL
                </button>
            </div>
          </header>

          <div className="flex gap-4 mb-6 border-b border-[var(--valo-gray-light)] pb-1">
             <button 
                onClick={() => setActiveTab('emails')}
                className={`pb-3 px-4 font-bold tracking-widest transition-all ${activeTab === 'emails' ? 'text-[var(--valo-red)] border-b-2 border-[var(--valo-red)]' : 'text-[var(--valo-text-dim)] hover:text-[var(--valo-text)]'}`}
             >
                 EMAILS
             </button>
             <button 
                onClick={() => setActiveTab('contacts')}
                className={`pb-3 px-4 font-bold tracking-widest transition-all ${activeTab === 'contacts' ? 'text-[var(--valo-cyan)] border-b-2 border-[var(--valo-cyan)]' : 'text-[var(--valo-text-dim)] hover:text-[var(--valo-text)]'}`}
             >
                 CONTACTS
             </button>
          </div>

          {activeTab === 'emails' && (
              <div className="flex gap-2 overflow-x-auto pb-4 scrollbar-hide mb-4">
                {['all', 'draft', 'scheduled', 'sent'].map(status => (
                  <button
                    key={status}
                    onClick={() => setEmailFilter(status)}
                    className={`px-4 py-1 text-xs font-bold tracking-wide uppercase transition-all tech-button ${
                      emailFilter === status
                        ? 'bg-[var(--valo-purple)] text-white'
                        : 'text-[var(--valo-text-dim)] border border-[var(--valo-gray-light)]'
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>
          )}

          <div className="space-y-3 pb-20">
            {loading ? (
              <div className="text-center py-12 text-[var(--valo-text-dim)]">
                <svg className="w-8 h-8 animate-spin mx-auto mb-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Decrypting...
              </div>
            ) : activeTab === 'emails' ? (
                emails.length === 0 ? (
                  <div className="tech-border p-8 text-center bg-[var(--valo-dark)]/50">
                    <div className="text-xl text-[var(--valo-text)]">No communications logged.</div>
                  </div>
                ) : (
                  <AnimatePresence mode="popLayout">
                    {emails.map((email, index) => (
                      <motion.div
                        key={email.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: Math.min(index * 0.05, 0.5) }}
                        className="tech-border p-5 bg-[var(--valo-dark)]/30 hover:bg-[var(--valo-dark)]/50 transition-colors border-l-4 border-l-[var(--valo-purple)]"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="font-bold text-[var(--valo-text)] text-lg">{email.subject}</h3>
                          <span className={`px-2 py-0.5 text-xs font-bold uppercase tracking-wider border ${getStatusStyle(email.status)}`}>
                            {email.status}
                          </span>
                        </div>
                        <p className="text-[var(--valo-text-dim)] text-sm mb-4 line-clamp-2">{email.body}</p>
                        <div className="flex justify-between items-center text-xs text-[var(--valo-text-dim)] font-mono">
                             <span>ID: {email.id.substring(0, 8)}</span>
                             <span>{new Date(email.created_at).toLocaleDateString()}</span>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                )
            ) : (
                contacts.length === 0 ? (
                    <div className="tech-border p-8 text-center bg-[var(--valo-dark)]/50">
                        <div className="text-xl text-[var(--valo-text)]">No contacts in database. Click "FIND TARGETS".</div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {contacts.map((contact, index) => (
                            <motion.div
                                key={contact.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.05 }}
                                className="tech-border p-4 bg-[var(--valo-dark)]/30 border-l-4 border-l-[var(--valo-cyan)]"
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="font-bold text-[var(--valo-text)]">{contact.name}</h3>
                                        <p className="text-sm text-[var(--valo-cyan)]">{contact.title}</p>
                                        <p className="text-xs text-[var(--valo-text-dim)] uppercase tracking-wide mt-1">{contact.company}</p>
                                    </div>
                                    <a href={`mailto:${contact.email}`} className="text-[var(--valo-text-dim)] hover:text-[var(--valo-white)]">
                                        ✉️
                                    </a>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )
            )}
          </div>
        </main>
        
        {/* Scrape Modal */}
        {showScrapeModal && (
            <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4">
                <div className="bg-[var(--valo-dark)] border border-[var(--valo-cyan)] p-8 max-w-md w-full relative tech-border shadow-[0_0_50px_rgba(34,211,238,0.2)]">
                    <h2 className="font-display text-2xl font-bold text-[var(--valo-text)] mb-6">INITIATE SCAN</h2>
                    <input 
                        type="text" 
                        placeholder="TARGET COMPANY (e.g. Google)"
                        value={scrapeCompany}
                        onChange={(e) => setScrapeCompany(e.target.value)}
                        className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white mb-6 focus:border-[var(--valo-cyan)] outline-none font-mono"
                    />
                    <div className="flex justify-end gap-4">
                        <button onClick={() => setShowScrapeModal(false)} className="text-[var(--valo-text-dim)] hover:text-white font-bold">CANCEL</button>
                        <button onClick={handleScrape} className="bg-[var(--valo-cyan)] text-black px-6 py-2 font-bold hover:brightness-110">DEPLOY SCANNET</button>
                    </div>
                </div>
            </div>
        )}

        {/* Manual Contact Modal */}
        {showManualModal && (
            <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[200] flex items-center justify-center p-4">
                <div className="bg-[var(--valo-dark)] border border-[var(--valo-white)] p-8 max-w-md w-full relative tech-border">
                    <h2 className="font-display text-2xl font-bold text-[var(--valo-text)] mb-6">NEW ASSET</h2>
                    <div className="space-y-4 mb-6">
                        <input type="text" placeholder="NAME" className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none" value={manualContact.name} onChange={e => setManualContact({...manualContact, name: e.target.value})} />
                        <input type="email" placeholder="EMAIL" className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none" value={manualContact.email} onChange={e => setManualContact({...manualContact, email: e.target.value})} />
                        <input type="text" placeholder="TITLE" className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none" value={manualContact.title} onChange={e => setManualContact({...manualContact, title: e.target.value})} />
                        <input type="text" placeholder="COMPANY" className="w-full bg-black/30 border border-[var(--valo-gray)] p-3 text-white outline-none" value={manualContact.company} onChange={e => setManualContact({...manualContact, company: e.target.value})} />
                    </div>
                    <div className="flex justify-end gap-4">
                        <button onClick={() => setShowManualModal(false)} className="text-[var(--valo-text-dim)] hover:text-white font-bold">CANCEL</button>
                        <button onClick={handleManualAdd} className="bg-[var(--valo-white)] text-black px-6 py-2 font-bold hover:brightness-110">REGISTER</button>
                    </div>
                </div>
            </div>
        )}

        {/* Success Toast */}
        <AnimatePresence>
            {showToast && (
                <motion.div 
                    initial={{ y: 50, opacity: 0 }} 
                    animate={{ y: 0, opacity: 1 }} 
                    exit={{ y: 20, opacity: 0 }}
                    className="fixed bottom-10 left-1/2 -translate-x-1/2 bg-[var(--valo-cyan)] text-black font-bold px-8 py-3 z-[300] shadow-[0_0_20px_rgba(34,211,238,0.5)]"
                    style={{ clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' }}
                >
                    {toastMessage}
                </motion.div>
            )}
        </AnimatePresence>
      </div>
    </div>
  );
}
