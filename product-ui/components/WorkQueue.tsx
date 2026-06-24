"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchJobLogs } from "@/lib/api";
import type { Job } from "@/lib/types";

function formatCommand(command: string[] | string) {
  if (Array.isArray(command)) return command.join(" ");
  return command;
}

function statusClass(status: string) {
  if (status === "success") return "job-status-success";
  if (status === "failed" || status === "timeout" || status === "cancelled") {
    return "job-status-failed";
  }
  if (status === "running" || status === "queued") return "job-status-running";
  return "job-status-neutral";
}

export function WorkQueue({ jobs = [] }: { jobs?: Job[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(jobs[0]?.id || null);
  const [logText, setLogText] = useState("");

  const selectedJob = useMemo(() => {
    if (!jobs.length) return undefined;
    return jobs.find((job) => job.id === selectedId) || jobs[0];
  }, [jobs, selectedId]);

  useEffect(() => {
    if (!jobs.length) {
      setSelectedId(null);
      setLogText("");
      return;
    }

    if (!selectedId || !jobs.some((job) => job.id === selectedId)) {
      setSelectedId(jobs[0].id);
    }
  }, [jobs, selectedId]);

  useEffect(() => {
    let cancelled = false;

    async function loadLog() {
      if (!selectedJob?.id) {
        setLogText("");
        return;
      }

      const text = await fetchJobLogs(selectedJob.id);

      if (!cancelled) {
        setLogText(text || "$ waiting for job output...");
      }
    }

    void loadLog();

    const timer = window.setInterval(() => {
      if (selectedJob?.status === "running" || selectedJob?.status === "queued") {
        void loadLog();
      }
    }, 1500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedJob?.id, selectedJob?.status]);

  return (
    <section className="work-queue-panel">
      <div className="work-queue-head">
        <div>
          <div className="product-kicker">Jobs</div>
          <h2>Work queue & logs</h2>
        </div>
      </div>

      <div className="work-queue-layout">
        <div className="work-queue-table">
          <div className="work-queue-row work-queue-row-head">
            <span>Action</span>
            <span>Status</span>
            <span>Code</span>
            <span>Command</span>
          </div>

          <div className="work-queue-list">
            {jobs.map((job) => (
              <button
                key={job.id}
                type="button"
                className={`work-queue-row work-queue-item ${
                  selectedJob?.id === job.id ? "is-selected" : ""
                }`}
                onClick={() => setSelectedId(job.id)}
              >
                <span>
                  <strong>{job.action}</strong>
                  <em>{job.id}</em>
                </span>

                <span>
                  <b className={statusClass(job.status)}>{job.status}</b>
                </span>

                <span>{job.code ?? "–"}</span>

                <code>{formatCommand(job.command)}</code>
              </button>
            ))}

            {jobs.length === 0 ? (
              <div className="work-queue-empty">No jobs yet.</div>
            ) : null}
          </div>
        </div>

        <pre className="work-queue-log">
{logText || "$ waiting for job output..."}
        </pre>
      </div>
    </section>
  );
}
