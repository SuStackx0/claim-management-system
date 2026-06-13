import { useEffect, useState } from "react";
import { apiGet, apiPostForm } from "../api/client";
import type { Member, ClaimOutcome } from "../api/types";
import DecisionCard from "../components/DecisionCard";

const CLAIM_CATEGORIES = [
  "CONSULTATION",
  "DIAGNOSTIC",
  "PHARMACY",
  "DENTAL",
  "VISION",
  "ALTERNATIVE_MEDICINE",
];

const STAGES: { name: string; desc: string }[] = [
  { name: "Intake", desc: "Validating member, policy & required documents" },
  { name: "Documents", desc: "Reading uploaded bills, prescriptions & reports" },
  { name: "Extraction", desc: "Extracting structured fields from documents" },
  { name: "Consistency", desc: "Cross-checking amounts, dates & member details" },
  { name: "Adjudication", desc: "Applying policy rules & computing the payout" },
  { name: "Fraud", desc: "Scanning for anomalies & duplicate claims" },
  { name: "Decision", desc: "Finalising the outcome & member message" },
];

const today = () => new Date().toISOString().slice(0, 10);

export default function SubmitClaim() {
  const [members, setMembers] = useState<Member[]>([]);
  const [membersLoading, setMembersLoading] = useState(true);
  const [membersError, setMembersError] = useState<string | null>(null);

  const [memberId, setMemberId] = useState("");
  const [claimCategory, setClaimCategory] = useState(CLAIM_CATEGORIES[0]);
  const [treatmentDate, setTreatmentDate] = useState(today());
  const [amount, setAmount] = useState("");
  const [hospital, setHospital] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<ClaimOutcome | null>(null);

  useEffect(() => {
    let active = true;
    apiGet<Member[]>("/members")
      .then((data) => {
        if (!active) return;
        setMembers(data);
        if (data.length > 0) setMemberId(data[0].member_id);
        setMembersLoading(false);
      })
      .catch((e) => {
        if (!active) return;
        setMembersError(e instanceof Error ? e.message : String(e));
        setMembersLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (files.length === 0) {
      setError("Attach at least one supporting document");
      return;
    }

    setProcessing(true);
    setOutcome(null);

    const payload = {
      member_id: memberId,
      policy_id: "PLUM_GHI_2024",
      claim_category: claimCategory,
      treatment_date: treatmentDate,
      claimed_amount: Number(amount),
      hospital_name: hospital || null,
    };

    const form = new FormData();
    form.append("payload", JSON.stringify(payload));
    for (const file of files) {
      form.append("files", file);
    }

    try {
      const out = await apiPostForm<ClaimOutcome>("/claims/upload", form);
      setOutcome(out);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div>
      <h1>Submit a Claim</h1>
      <p className="pc-caption">
        Fill in the details, attach supporting documents, and the AI pipeline
        will adjudicate in 15–25 seconds.
      </p>
      <hr className="pc-divider" />

      {membersError && (
        <div className="pc-alert pc-alert-error">{membersError}</div>
      )}

      <form onSubmit={onSubmit}>
        <div className="pc-grid">
          <div className="pc-field">
            <label className="pc-label">Member</label>
            {membersLoading ? (
              <div className="pc-help">Loading members…</div>
            ) : (
              <select
                className="pc-select"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
              >
                {members.map((m) => (
                  <option key={m.member_id} value={m.member_id}>
                    {`${m.member_id} — ${m.name}`}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="pc-field">
            <label className="pc-label">Claim Category</label>
            <select
              className="pc-select"
              value={claimCategory}
              onChange={(e) => setClaimCategory(e.target.value)}
            >
              {CLAIM_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="pc-field">
            <label className="pc-label">Treatment Date</label>
            <input
              type="date"
              className="pc-input"
              value={treatmentDate}
              onChange={(e) => setTreatmentDate(e.target.value)}
            />
          </div>

          <div className="pc-field">
            <label className="pc-label">Claimed Amount (₹)</label>
            <input
              type="number"
              min={0}
              step={100}
              className="pc-input"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          <div className="pc-field">
            <label className="pc-label">Hospital / Provider Name</label>
            <input
              type="text"
              className="pc-input"
              value={hospital}
              onChange={(e) => setHospital(e.target.value)}
              placeholder="e.g. Apollo Hospitals, Chennai"
            />
          </div>

          <div className="pc-field pc-field-full">
            <label className="pc-label">Supporting Documents</label>
            <div className="pc-filedrop">
              <input
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) =>
                  setFiles(e.target.files ? Array.from(e.target.files) : [])
                }
              />
            </div>
            {files.length > 0 && (
              <ul className="pc-filelist">
                {files.map((f, i) => (
                  <li key={`${f.name}-${i}`}>{f.name}</li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <button
          className="pc-btn pc-btn-full"
          type="submit"
          disabled={processing}
        >
          Submit Claim
        </button>
      </form>

      {error && <div className="pc-alert pc-alert-error">{error}</div>}

      {processing && (
        <div className="pc-card">
          <h3>
            <span className="pc-spinner" /> Processing claim through the AI
            pipeline
          </h3>
          <p className="pc-caption">This usually takes ~15–25 seconds.</p>
          <div>
            {STAGES.map((s, i) => (
              <div className="pc-stage" key={s.name}>
                <span className="pc-stage-n">{i + 1}.</span>{" "}
                <span className="pc-stage-name">{s.name}</span>{" "}
                <span className="pc-stage-desc">— {s.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {outcome && (
        <>
          <hr className="pc-divider" />
          <DecisionCard outcome={outcome} />
        </>
      )}
    </div>
  );
}
