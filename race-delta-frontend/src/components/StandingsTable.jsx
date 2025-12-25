import { useEffect, useState } from "react";
import { fetchDriverStandings } from "../lib/api";

export default function StandingsTable() {
  const [standings, setStandings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDriverStandings().then(data => {
      setStandings(data.standings || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <p>Loading standings...</p>;

  return (
    <div className="standings-table">
      <h2>Driver Standings</h2>

      <table>
        <thead>
          <tr>
            <th>Pos</th>
            <th>Driver</th>
            <th>Team</th>
            <th>Points</th>
            <th>Wins</th>
          </tr>
        </thead>

        <tbody>
          {standings.map(driver => (
            <tr key={driver.driver_code}>
              <td>{driver.position}</td>
              <td>{driver.driver_name}</td>
              <td>{driver.team}</td>
              <td>{driver.points}</td>
              <td>{driver.wins}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
