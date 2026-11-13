import '../remodel.css'

// Placeholder About / founder page (DESIGN.md).
export default function About() {
  return (
    <section className="remodel">
      <div className="remodel-inner">
        <p className="remodel-eyebrow">Who built this</p>
        <div className="remodel-photo" aria-hidden="true">[your photo]</div>
        <h1 className="remodel-heading">
          [Your name] — <em>[title]</em>
        </h1>
        <p className="remodel-body">
          [One line of bio: who you are and why you built FormCast.]
        </p>
        <p className="remodel-note">Placeholder — built in the remodel (see ROADMAP queue b)</p>
      </div>
    </section>
  )
}
