import '../remodel.css'

// About / founder page (DESIGN.md).
export default function About() {
  return (
    <section className="remodel">
      <div className="remodel-inner">
        <p className="remodel-eyebrow">Who built this</p>
        <img src="/conaire.jpg" alt="Conaire Molloy" className="remodel-photo" />
        <h1 className="remodel-heading">
          Conaire Molloy — <em>Data Analyst</em>
        </h1>
        <p className="remodel-body">
          Data analyst with a maths and finance background. Built the
          five-model ensemble solo. No tipping service — just a model, and every
          result logged publicly.
        </p>
      </div>
    </section>
  )
}
