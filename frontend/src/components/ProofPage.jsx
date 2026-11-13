import '../remodel.css'

// Placeholder public proof page — the Prediction Log becomes this (DESIGN.md).
// No figures here on purpose: claims come from ROADMAP "Current State & Honest Claims".
export default function ProofPage() {
  return (
    <section className="remodel">
      <div className="remodel-inner">
        <p className="remodel-eyebrow">The public ledger</p>
        <h1 className="remodel-heading">
          [Verifiable-record <em>headline</em>]
        </h1>
        <p className="remodel-body">
          A summary of the record goes here; the full log sits behind “View full log”.
        </p>
        <p className="remodel-note">Placeholder — built in the remodel (see ROADMAP queue b)</p>
      </div>
    </section>
  )
}
