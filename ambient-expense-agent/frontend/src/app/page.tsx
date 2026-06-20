"use client";

import { useEffect, useState, FormEvent } from "react";
import styles from "./page.module.css";

interface Session {
  id: string;
  user_id: string;
  events: any[];
  state: any;
}

interface PendingReview {
  sessionId: string;
  expense: any;
  riskLevel: string;
  riskFactors: string[];
  summary: string;
}

interface AllExpenseItem {
  sessionId: string;
  expense: any;
  status: string;
  lastUpdateTime: number;
}

export default function Home() {
  const [amount, setAmount] = useState("150");
  const [submitter, setSubmitter] = useState("employee@company.com");
  const [description, setDescription] = useState("Team dinner");
  const [reviews, setReviews] = useState<PendingReview[]>([]);
  const [allExpenses, setAllExpenses] = useState<AllExpenseItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const fetchSessions = async () => {
    setSyncing(true);
    try {
        const res = await fetch("http://127.0.0.1:8080/apps/expense_agent/users/user/sessions");
        if (!res.ok) return;
        const data = await res.json();
        
        // Find sessions that have a pending approval_decision
        const pending: PendingReview[] = [];
        const allItems: AllExpenseItem[] = [];
        
        const sessionList = Array.isArray(data) ? data : (data.sessions || []);
        for (const session of sessionList) {
          // Fetch full session details to get events
          const detailRes = await fetch(`http://127.0.0.1:8080/apps/expense_agent/users/user/sessions/${session.id}`);
          if (!detailRes.ok) continue;
          const detail = await detailRes.json();
          
          const events = detail.events || [];
          const hasEvents = events.length > 0;
          const latestEvent = hasEvents ? events[events.length - 1] : null;
          const hasPendingReview = latestEvent?.longRunningToolIds?.includes("approval_decision");
          
          let status = "Unknown";
          if (hasPendingReview) {
            status = "Pending Review";
          } else if (detail.state?.review?.recommendation) {
            // Already processed and decision made (could be auto-approved or manual)
            status = detail.state.review.recommendation;
          } else if (!hasEvents) {
            status = "Processing...";
          } else {
            status = "Processed";
          }
          
          allItems.push({
            sessionId: session.id,
            expense: detail.state?.expense || {},
            status: status,
            lastUpdateTime: detail.lastUpdateTime || Date.now()
          });
          
          if (hasPendingReview) {
            // Extract expense and risk context from state
            pending.push({
              sessionId: session.id,
              expense: detail.state?.expense || {},
              riskLevel: detail.state?.risk_level || "UNKNOWN",
              riskFactors: detail.state?.risk_factors || [],
              summary: detail.state?.summary || "Pending review."
            });
          }
        }
        
        allItems.sort((a, b) => b.lastUpdateTime - a.lastUpdateTime);
        setAllExpenses(allItems);
        setReviews(pending);
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const triggerExpense = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    const expense = {
      amount: parseFloat(amount),
      submitter,
      category: "general",
      description,
      date: new Date().toISOString().split('T')[0]
    };
    
    const payload = {
      message: {
        data: btoa(JSON.stringify(expense)),
        attributes: { source: "nextjs-ui" }
      },
      subscription: `nextjs-${Date.now()}`
    };

    try {
      await fetch("http://127.0.0.1:8080/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      // Reset form slightly
      setDescription("");
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDecision = async (sessionId: string, decision: "yes" | "no") => {
    const payload = {
      app_name: "expense_agent",
      user_id: "user",
      session_id: sessionId,
      new_message: {
        role: "user",
        parts: [
          {
            functionResponse: {
              id: "approval_decision",
              name: "adk_request_input",
              response: { result: decision }
            }
          }
        ]
      }
    };

    try {
      await fetch(`http://127.0.0.1:8080/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      // Optimistically remove from list
      setReviews(prev => prev.filter(r => r.sessionId !== sessionId));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <main className={styles.main}>
      <div className={styles.header}>
        <h1 className={styles.title}>Ambient Expense Approvals</h1>
        <p className={styles.subtitle}>Powered by Google ADK</p>
      </div>

      <div className={styles.grid}>
        {/* Left Column: Trigger Form */}
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"></path></svg>
            New Expense
          </h2>
          <form className={styles.form} onSubmit={triggerExpense}>
            <div className={styles.inputGroup}>
              <label className={styles.label}>Amount ($)</label>
              <input 
                type="number" 
                className={styles.input} 
                value={amount} 
                onChange={e => setAmount(e.target.value)} 
                required 
              />
            </div>
            <div className={styles.inputGroup}>
              <label className={styles.label}>Submitter</label>
              <input 
                type="email" 
                className={styles.input} 
                value={submitter} 
                onChange={e => setSubmitter(e.target.value)} 
                required 
              />
            </div>
            <div className={styles.inputGroup}>
              <label className={styles.label}>Description (Try a prompt injection!)</label>
              <textarea 
                className={styles.input} 
                rows={3} 
                value={description} 
                onChange={e => setDescription(e.target.value)} 
                required 
              />
            </div>
            <button type="submit" className={styles.button} disabled={loading}>
              {loading ? "Sending..." : "Submit to Agent"}
            </button>
          </form>
        </div>

        {/* Right Column: Inbox */}
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>
            <div className={styles.panelTitleLeft}>
              <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
              Review Inbox
            </div>
            <button className={styles.syncButton} onClick={fetchSessions} disabled={syncing}>
              <svg className={syncing ? styles.spin : ""} width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
              {syncing ? "Syncing..." : "Sync"}
            </button>
          </h2>
          
          <div className={styles.cardList}>
            {reviews.length === 0 ? (
              <div className={styles.emptyState}>
                <p>No expenses waiting for human review.</p>
                <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>Auto-approved items bypass this inbox completely!</p>
              </div>
            ) : (
              reviews.map(review => (
                <div key={review.sessionId} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <div>
                      <div className={styles.cardAmount}>${review.expense.amount?.toFixed(2)}</div>
                      <div className={styles.cardSubmitter}>{review.expense.submitter}</div>
                    </div>
                    {review.riskLevel && (
                      <div className={styles.badge}>
                        {review.riskLevel} RISK
                      </div>
                    )}
                  </div>
                  
                  <div className={styles.cardBody}>
                    <div style={{ marginBottom: '0.5rem' }}><strong>Description:</strong> {review.expense.description}</div>
                    <div style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}><strong>Agent Summary:</strong> {review.summary}</div>
                    {review.riskFactors.length > 0 && (
                      <div style={{ color: 'var(--danger)' }}>
                        <strong>Flags:</strong> {review.riskFactors.join(", ")}
                      </div>
                    )}
                  </div>
                  
                  <div className={styles.cardActions}>
                    <button className={`${styles.button} ${styles.success}`} style={{ flex: 1 }} onClick={() => handleDecision(review.sessionId, "yes")}>
                      Approve
                    </button>
                    <button className={`${styles.button} ${styles.danger}`} style={{ flex: 1 }} onClick={() => handleDecision(review.sessionId, "no")}>
                      Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      
      {/* Full Width Row: All Expenses History */}
      <div className={styles.panel} style={{ marginTop: "2rem" }}>
        <h2 className={styles.panelTitle}>
          <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          All Expenses History
        </h2>
        <div style={{ overflowX: "auto" }}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Submitter</th>
                <th>Amount</th>
                <th>Description</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {allExpenses.map(item => (
                <tr key={item.sessionId}>
                  <td><code className={styles.codeBadge}>{item.sessionId.slice(-8)}</code></td>
                  <td>{item.expense?.submitter || "Unknown"}</td>
                  <td>${item.expense?.amount?.toFixed(2) || "0.00"}</td>
                  <td>{item.expense?.description || "-"}</td>
                  <td>
                    <span className={
                      item.status.toLowerCase().includes("approve") ? styles.badgeSuccess :
                      item.status.toLowerCase().includes("reject") ? styles.badgeError :
                      styles.badgeWarning
                    }>
                      {item.status.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
              {allExpenses.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)" }}>
                    No expenses found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
