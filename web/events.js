"use strict";

// Club events, straight from hellorubric's own JSON API (the same call their
// site makes). It's CORS-open, so the static page can fetch it directly — no
// backend, nothing to maintain. If hellorubric ever changes it, the section
// degrades to a friendly fallback rather than erroring.
//
// Endpoint shape (discovered from their frontend):
//   POST https://api.hellorubric.com/
//   body: details={...,"societyid":"<id>",...}&endpoint=getSocietyLandingPage
// Response: { description, sections:[{ array:[ event, ... ] }] } where each
// event has: title, formatteddate, month, day, subtitle (location), image,
// destination (link), info (price/"Free"), upcoming (0/1).

const HR_ENDPOINT = "https://api.hellorubric.com/";
const HR_SOCIETY_ID = window.RBGA_HELLORUBRIC_SOCIETY || "10742";
const DISCORD_URL = window.RBGA_DISCORD_URL || "";

const eventsEl = document.getElementById("events");
const eventsStatusEl = document.getElementById("events-status");

const MONTHS = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
                 Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };

// Reconstruct a Date from month/day + the year in formatteddate ("…, 8 Jun 2026, …").
function eventDate(ev) {
  const m = MONTHS[ev.month];
  const d = parseInt(ev.day, 10);
  if (m == null || isNaN(d)) return null;
  const yr = /\b(20\d{2})\b/.exec(ev.formatteddate || "");
  const year = yr ? +yr[1] : new Date().getFullYear();
  return new Date(year, m, d);
}

// Trust hellorubric's flag, but also treat anything dated today-or-later as upcoming.
function isUpcoming(ev) {
  if (ev.upcoming === 1) return true;
  const dt = eventDate(ev);
  if (!dt) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dt >= today;
}

function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text != null) n.textContent = text;
  return n;
}

function makeEventCard(ev) {
  const card = el("a", "event-card");
  card.href = ev.destination || "#";
  card.target = "_blank";
  card.rel = "noopener";

  const date = el("div", "event-date");
  date.append(el("span", "event-month", ev.month || ""),
              el("span", "event-day", ev.day || ""));
  card.appendChild(date);

  const body = el("div", "event-body");
  body.appendChild(el("h3", "event-title", ev.title || "Event"));
  if (ev.formatteddate) body.appendChild(el("p", "event-when", ev.formatteddate));
  if (ev.subtitle) body.appendChild(el("p", "event-where", ev.subtitle));
  if (ev.info) body.appendChild(el("span", "event-info", ev.info));
  card.appendChild(body);
  return card;
}

// Shown when there are no upcoming events (or the fetch fails). Uses the club's
// own blurb from the API when we have it, so it's informative, not a dead end.
function emptyState(description) {
  const wrap = el("div", "events-empty");
  wrap.appendChild(el("p", null, description ||
    "No upcoming sessions are scheduled right now — check back soon."));
  if (DISCORD_URL) {
    const cta = el("a", "events-cta", "Join our Discord");
    cta.href = DISCORD_URL;
    cta.target = "_blank";
    cta.rel = "noopener";
    wrap.appendChild(cta);
  }
  return wrap;
}

async function loadEvents() {
  try {
    const details = {
      societyid: HR_SOCIETY_ID,
      domain: "campus.hellorubric.com",
      device: "web_portal",
      version: 4,
      timestamp: Date.now(),
    };
    // URLSearchParams keeps this a "simple" CORS request (no preflight).
    const body = new URLSearchParams({
      details: JSON.stringify(details),
      endpoint: "getSocietyLandingPage",
    });
    const res = await fetch(HR_ENDPOINT, { method: "POST", body });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const all = (data.sections || []).flatMap((s) => s.array || []);
    const upcoming = all
      .filter(isUpcoming)
      .sort((a, b) => (eventDate(a) || 0) - (eventDate(b) || 0)); // soonest first

    eventsStatusEl.textContent = "";
    if (upcoming.length) {
      eventsEl.replaceChildren(...upcoming.map(makeEventCard));
    } else {
      eventsEl.replaceChildren(emptyState(data.description));
    }
  } catch (err) {
    // Never alarm a visitor — fall back to the friendly empty state.
    eventsStatusEl.textContent = "";
    eventsEl.replaceChildren(emptyState(""));
  }
}

loadEvents();
