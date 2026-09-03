import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <div className="eyebrow eyebrow-red">Off track</div>
      <h1 className="page-title mt-2">404 <span className="dim">// page not found</span></h1>
      <p className="page-sub mx-auto mt-4">That page doesn't exist. Head back to the dashboard to pick a race, driver or tool.</p>
      <Link to="/" className="btn-primary mt-8">Back to the dashboard</Link>
    </div>
  );
}
