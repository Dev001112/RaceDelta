/* Shared page header: red eyebrow, condensed italic title with the "//season" slash, subtitle, actions. */
export default function PageHeader({ kicker, title, season, subtitle, actions, tourId }) {
  return (
    <header className="page-header" data-tour={tourId}>
      <div>
        {kicker && <div className="eyebrow eyebrow-red">{kicker}</div>}
        <h1 className="page-title">
          {title}
          {season ? <span className="dim"> //{season}</span> : null}
        </h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
