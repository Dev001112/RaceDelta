import React, { createContext, useContext, useEffect, useState } from "react";
import client from "../api/client";

const SeasonContext = createContext();

export function SeasonProvider({ children }) {
    const [season, setSeason] = useState(null); // The currently selected season (int)
    const [seasonOptions, setSeasonOptions] = useState([]); // Dropdown options
    const [loading, setLoading] = useState(true);
    const [isOffseason, setIsOffseason] = useState(false);
    const [displaySeason, setDisplaySeason] = useState(null); // The recommended display season
    const [calendarSeason, setCalendarSeason] = useState(null);

    useEffect(() => {
        let mounted = true;

        client.fetchSeasons()
            .then((data) => {
                if (!mounted) return;

                setSeasonOptions(data.seasons_dropdown || []);
                setDisplaySeason(data.display_season);
                setIsOffseason(data.is_offseason);
                setCalendarSeason(data.calendar_season);

                // Set default season
                setSeason(data.display_season);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to fetch seasons", err);
                if (mounted) {
                    const fallbackYear = new Date().getFullYear();
                    setSeason(fallbackYear);
                    setDisplaySeason(fallbackYear);
                    setLoading(false);
                }
            });

        return () => { mounted = false; };
    }, []);

    const value = {
        season,
        setSeason,
        seasonOptions,
        loading,
        isOffseason,
        displaySeason,
        calendarSeason
    };

    return (
        <SeasonContext.Provider value={value}>
            {children}
        </SeasonContext.Provider>
    );
}

export function useSeason() {
    const context = useContext(SeasonContext);
    if (context === undefined) {
        throw new Error("useSeason must be used within a SeasonProvider");
    }
    return context;
}
