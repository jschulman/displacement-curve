/* ============================================================
   The Displacement Curve — Dashboard Logic
   Vanilla JS, Chart.js, no frameworks, no tracking
   ============================================================ */

(function () {
  "use strict";

  // ---- Data paths (relative to docs/) ----
  const DATA_PATHS = {
    employment: "data/bls/processed/employment.json",
    trends: "data/trends/processed/search_interest.json",
    github: "data/github/processed/activity.json",
    earnings: "data/earnings/processed/revenue.json",
    workforce: "data/sec/processed/workforce.json",
    vc: "data/vc/processed/funding.json",
    jobs: "data/jobs/processed/postings.json",
    regulatory: "data/regulatory/processed/guidance.json",
    composite: "data/composite/displacement_index.json",
    inflection: "data/composite/inflection_distance.json",
    youth: "data/apprenticeship/processed/collapse.json",
  };

  // ---- State ----
  let state = {
    data: { employment: null, trends: null, github: null, earnings: null, workforce: null, vc: null, jobs: null, regulatory: null, composite: null, inflection: null, youth: null },
    expandedSignal: null,
    sparkCharts: {},
    expandedChart: null,
  };

  // ---- Utility Functions ----

  function formatNumber(n) {
    if (n == null) return "--";
    return n.toLocaleString("en-US");
  }

  function formatCompact(n) {
    if (n == null) return "--";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return Math.round(n).toLocaleString("en-US") + "";
    return n.toString();
  }

  function formatStars(n) {
    if (n == null) return "--";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return Math.round(n / 1000) + "K";
    return n.toString();
  }

  function changeArrow(delta) {
    if (delta > 0) return { arrow: "\u2191", cls: "positive" };
    if (delta < 0) return { arrow: "\u2193", cls: "negative" };
    return { arrow: "\u2192", cls: "neutral" };
  }

  function formatDate(dateStr) {
    if (!dateStr) return "--";
    // Handle quarterly format like "2025-Q4"
    var qMatch = dateStr.match(/^(\d{4})-Q(\d)$/);
    if (qMatch) {
      return "Q" + qMatch[2] + " " + qMatch[1];
    }
    var parts = dateStr.split("-");
    var months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    var monthIdx = parseInt(parts[1], 10) - 1;
    var year = parts[0];
    if (parts.length === 3) {
      return months[monthIdx] + " " + parseInt(parts[2], 10) + ", " + year;
    }
    return months[monthIdx] + " " + year;
  }

  function last(arr, n) {
    if (!arr || arr.length === 0) return [];
    return arr.slice(Math.max(0, arr.length - n));
  }

  // ---- Chart.js defaults for dark mode ----
  function setChartDefaults() {
    Chart.defaults.color = "#8b949e";
    Chart.defaults.borderColor = "rgba(48, 54, 61, 0.5)";
    Chart.defaults.font.family =
      'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  }

  // ---- Sparkline Chart Factory ----
  function createSparkline(canvasId, labels, data, color) {
    var ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    if (state.sparkCharts[canvasId]) {
      state.sparkCharts[canvasId].destroy();
    }

    var chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            data: data,
            borderColor: color || "#58a6ff",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 0,
            pointHitRadius: 0,
            tension: 0.3,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false },
        },
        scales: {
          x: { display: false },
          y: { display: false },
        },
        interaction: { enabled: false },
        animation: { duration: 600 },
      },
    });

    state.sparkCharts[canvasId] = chart;
    return chart;
  }

  // ---- Data Extraction Helpers ----

  function getEmploymentSummary(empData) {
    // Primary series: CES6000000001 (Professional & Business Services total)
    var primaryKey = "CES6000000001";
    var series = null;

    if (empData && empData.series) {
      // Try exact key
      if (empData.series[primaryKey]) {
        series = empData.series[primaryKey];
      } else {
        // Fallback: use first series
        var keys = Object.keys(empData.series);
        if (keys.length > 0) {
          series = empData.series[keys[0]];
        }
      }
    }

    if (!series || !series.data || series.data.length === 0) {
      return null;
    }

    var sorted = series.data.slice().sort(function (a, b) {
      return a.date.localeCompare(b.date);
    });

    var trailing12 = last(sorted, 12);
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var mom = prev ? latest.value - prev.value : 0;

    return {
      value: latest.value,
      formatted: formatNumber(latest.value) + "K",
      mom: mom,
      momFormatted: (mom >= 0 ? "+" : "") + formatNumber(mom) + "K",
      date: latest.date,
      sparkLabels: trailing12.map(function (d) { return d.date; }),
      sparkData: trailing12.map(function (d) { return d.value; }),
    };
  }

  function getTrendsSummary(trendsData) {
    if (!trendsData || !trendsData.categories) return null;

    var categories = trendsData.categories;
    var catKeys = Object.keys(categories);
    if (catKeys.length === 0) return null;

    // Build date-indexed composite
    var dateMap = {};
    catKeys.forEach(function (key) {
      var catData = categories[key].composite || categories[key].data || categories[key];
      if (Array.isArray(catData)) {
        catData.forEach(function (point) {
          if (!dateMap[point.date]) {
            dateMap[point.date] = { sum: 0, count: 0 };
          }
          dateMap[point.date].sum += point.value;
          dateMap[point.date].count += 1;
        });
      }
    });

    var dates = Object.keys(dateMap).sort();
    var composite = dates.map(function (d) {
      return {
        date: d,
        value: Math.round(dateMap[d].sum / dateMap[d].count),
      };
    });

    if (composite.length === 0) return null;

    var trailing12 = last(composite, 12);
    var latest = composite[composite.length - 1];
    var prev = composite.length >= 2 ? composite[composite.length - 2] : null;
    var mom = prev ? latest.value - prev.value : 0;

    return {
      value: latest.value,
      formatted: latest.value.toString(),
      mom: mom,
      momFormatted: (mom >= 0 ? "+" : "") + mom,
      date: latest.date,
      sparkLabels: trailing12.map(function (d) { return d.date; }),
      sparkData: trailing12.map(function (d) { return d.value; }),
    };
  }

  function getGithubSummary(ghData) {
    var monthly = ghData && (ghData.monthly || ghData.aggregate);
    if (!monthly || monthly.length === 0) return null;

    var sorted = monthly.slice().sort(function (a, b) {
      return a.date.localeCompare(b.date);
    });

    var trailing12 = last(sorted, 12);
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var reposKey = latest.new_repos != null ? "new_repos" : "total_new_repos";
    var starsKey = latest.cumulative_stars != null ? "cumulative_stars" : "total_stars";
    var momRepos = prev ? latest[reposKey] - prev[reposKey] : 0;

    return {
      value: latest[starsKey],
      formatted: formatStars(latest[starsKey]) + " \u2605",
      mom: momRepos,
      momFormatted: (momRepos >= 0 ? "+" : "") + momRepos + " repos",
      date: latest.date,
      sparkLabels: trailing12.map(function (d) { return d.date; }),
      sparkData: trailing12.map(function (d) { return d[starsKey]; }),
    };
  }

  function getEarningsSummary(earningsData) {
    if (!earningsData || !earningsData.aggregate || earningsData.aggregate.length === 0) return null;

    var sorted = earningsData.aggregate.slice().sort(function(a, b) {
      return a.quarter.localeCompare(b.quarter);
    });

    // Filter to entries with revenue per employee data (real data may lack ai_revenue)
    var withData = sorted.filter(function(d) {
      return d.avg_rev_per_employee != null || d.total_ai_revenue_mm != null;
    });
    if (withData.length === 0) return null;

    var trailing = last(withData, 8);
    var latest = withData[withData.length - 1];
    var prev = withData.length >= 2 ? withData[withData.length - 2] : null;

    // Prefer total_ai_revenue_mm, fall back to avg_rev_per_employee for display
    var val = latest.total_ai_revenue_mm;
    if (val != null) {
      var mom = prev && prev.total_ai_revenue_mm != null ? val - prev.total_ai_revenue_mm : 0;
      return {
        value: val,
        formatted: "$" + formatCompact(val) + "M",
        mom: mom,
        momFormatted: (mom >= 0 ? "+" : "") + "$" + Math.abs(mom) + "M QoQ",
        date: latest.quarter,
        sparkLabels: trailing.map(function(d) { return d.quarter; }),
        sparkData: trailing.map(function(d) { return d.total_ai_revenue_mm || 0; }),
      };
    } else {
      // Fall back to rev per employee as the card metric
      var rpe = latest.avg_rev_per_employee || 0;
      var prevRpe = prev && prev.avg_rev_per_employee != null ? prev.avg_rev_per_employee : rpe;
      var mom = rpe - prevRpe;
      return {
        value: rpe,
        formatted: "$" + rpe.toFixed(0) + "K/emp",
        mom: mom,
        momFormatted: (mom >= 0 ? "+" : "") + "$" + Math.abs(mom).toFixed(1) + "K QoQ",
        date: latest.quarter,
        sparkLabels: trailing.map(function(d) { return d.quarter; }),
        sparkData: trailing.map(function(d) { return d.avg_rev_per_employee || 0; }),
      };
    }
  }

  function getWorkforceSummary(earningsData) {
    if (!earningsData || !earningsData.aggregate || earningsData.aggregate.length === 0) return null;

    var sorted = earningsData.aggregate.slice().sort(function(a, b) {
      return a.quarter.localeCompare(b.quarter);
    });

    // Filter to entries with rev per employee data
    var withData = sorted.filter(function(d) { return d.avg_rev_per_employee != null; });
    if (withData.length === 0) return null;

    var trailing = last(withData, 8);
    var latest = withData[withData.length - 1];
    var prev = withData.length >= 2 ? withData[withData.length - 2] : null;
    var mom = prev ? (latest.avg_rev_per_employee - prev.avg_rev_per_employee) : 0;

    return {
      value: latest.avg_rev_per_employee,
      formatted: "$" + latest.avg_rev_per_employee.toFixed(1) + "K",
      mom: mom,
      momFormatted: (mom >= 0 ? "+" : "") + "$" + Math.abs(mom).toFixed(1) + "K QoQ",
      date: latest.quarter,
      sparkLabels: trailing.map(function(d) { return d.quarter; }),
      sparkData: trailing.map(function(d) { return d.avg_rev_per_employee || 0; }),
    };
  }

  function getVcSummary(vcData) {
    if (!vcData || !vcData.aggregate || vcData.aggregate.length === 0) return null;

    var sorted = vcData.aggregate.slice().sort(function(a, b) {
      return a.quarter.localeCompare(b.quarter);
    });

    var trailing = last(sorted, 8);
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var qoq = prev ? latest.total_funding_mm - prev.total_funding_mm : 0;

    return {
      value: latest.total_funding_mm,
      formatted: "$" + Math.round(latest.total_funding_mm) + "M",
      mom: qoq,
      momFormatted: (qoq >= 0 ? "+" : "") + "$" + Math.abs(Math.round(qoq)) + "M QoQ",
      date: latest.quarter,
      sparkLabels: trailing.map(function(d) { return d.quarter; }),
      sparkData: trailing.map(function(d) { return d.total_funding_mm; }),
    };
  }

  function getJobsSummary(jobsData) {
    if (!jobsData || !jobsData.monthly || jobsData.monthly.length === 0) return null;

    var sorted = jobsData.monthly.slice().sort(function(a, b) {
      return a.date.localeCompare(b.date);
    });

    // Field is openings_index in current data; legacy data still has it
    // under the old (misleading) name ai_to_traditional_ratio.
    function idx(entry) {
      return entry.openings_index != null ? entry.openings_index : entry.ai_to_traditional_ratio;
    }

    var trailing = last(sorted, 12);
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var latestVal = idx(latest);
    var prevVal = prev ? idx(prev) : null;
    var mom = prevVal != null && latestVal != null ? latestVal - prevVal : 0;

    return {
      value: latestVal,
      formatted: latestVal != null ? latestVal.toFixed(3) + "x" : "--",
      mom: mom,
      momFormatted: (mom >= 0 ? "+" : "") + mom.toFixed(3) + " MoM",
      date: latest.date,
      sparkLabels: trailing.map(function(d) { return d.date; }),
      sparkData: trailing.map(idx),
    };
  }

  // ---- Apprenticeship Pipeline (youth share of professional services, Census ACS) ----
  function getYouthSummary(youthData) {
    if (!youthData || !youthData.monthly || youthData.monthly.length === 0) return null;
    var sorted = youthData.monthly.slice().sort(function (a, b) { return a.date.localeCompare(b.date); });
    function pct(e) { var v = e.youth_share_u25 != null ? e.youth_share_u25 : e.value; return v != null ? v * 100 : null; }
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var latestVal = pct(latest);
    var prevVal = prev ? pct(prev) : null;
    var mom = (prevVal != null && latestVal != null) ? latestVal - prevVal : 0; // percentage points, YoY
    return {
      value: latestVal,
      formatted: latestVal != null ? latestVal.toFixed(1) + "% under 25" : "--",
      mom: mom,
      momFormatted: (mom >= 0 ? "+" : "") + mom.toFixed(1) + " pt YoY",
      date: latest.date,
      sparkLabels: sorted.map(function (d) { return d.date; }),
      sparkData: sorted.map(pct),
    };
  }

  // ---- Phase Descriptions ----
  var PHASE_INFO = {
    "Pre-disruption": "AI is a topic, not a force. Business as usual.",
    "Productivity": "AI is making firms more efficient. Employment stable or growing.",
    "Erosion": "Revenue per employee diverging from headcount. Job mix shifting.",
    "Displacement": "Employment declining. Funding pouring into replacements.",
  };

  // ---- Regulatory Summary ----
  function getRegulatorySummary(regData) {
    if (!regData || !regData.aggregate || regData.aggregate.length === 0) return null;

    var sorted = regData.aggregate.slice().sort(function(a, b) {
      return a.quarter.localeCompare(b.quarter);
    });

    var trailing = last(sorted, 8);
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var qoq = prev ? latest.total_documents - prev.total_documents : 0;

    return {
      value: latest.total_documents,
      formatted: latest.total_documents + " docs",
      mom: qoq,
      momFormatted: (qoq >= 0 ? "+" : "") + qoq + " QoQ",
      date: latest.quarter,
      sparkLabels: trailing.map(function(d) { return d.quarter; }),
      sparkData: trailing.map(function(d) { return d.cumulative_documents; }),
    };
  }

  // ---- Hero Score Rendering ----
  function renderHeroScore(compositeData) {
    if (!compositeData || !compositeData.monthly || compositeData.monthly.length === 0) return;

    var sorted = compositeData.monthly.slice().sort(function(a, b) {
      return a.date.localeCompare(b.date);
    });

    var latest = sorted[sorted.length - 1];
    var scoreEl = document.getElementById("hero-score");
    var phaseEl = document.getElementById("hero-phase");
    var descEl = document.getElementById("hero-description");
    var trendEl = document.getElementById("hero-trend");

    if (!scoreEl) return;

    scoreEl.textContent = latest.score.toFixed(1);

    // Score color
    if (latest.score < 50) {
      scoreEl.style.color = "var(--green)";
    } else if (latest.score <= 75) {
      scoreEl.style.color = "#f0883e";
    } else {
      scoreEl.style.color = "var(--red)";
    }

    phaseEl.textContent = latest.phase;
    descEl.textContent = PHASE_INFO[latest.phase] || "";

    // Trend
    var trendArrow = "\u2192";
    var trendLabel = "Flat";
    var trendColor = "var(--neutral)";
    if (latest.trend === "up") {
      trendArrow = "\u2191";
      trendLabel = "Rising";
      trendColor = "var(--red)";
    } else if (latest.trend === "down") {
      trendArrow = "\u2193";
      trendLabel = "Falling";
      trendColor = "var(--green)";
    }
    trendEl.textContent = trendArrow + " Trend: " + trendLabel;
    trendEl.style.color = trendColor;
  }

  // ---- Apprenticeship Inflection Distance (analog of quantum-qanary Q-Day Distance) ----
  function renderInflection(data) {
    var el = document.getElementById("inflection-section");
    if (!el) return;
    if (!data || !data.estimate || !data.components || !data.components.crossover) {
      el.style.display = "none";
      return;
    }
    el.style.display = "";
    var est = data.estimate;
    var cx = data.components.crossover;
    var set = function (id, txt) { var n = document.getElementById(id); if (n) n.textContent = txt; };
    set("inflection-range", est.crossover_year_low + "–" + est.crossover_year_high);
    set("inflection-mid", "midpoint " + est.crossover_year_mid + " · ~" + est.midpoint_years + " yrs out");
    set("inflection-progress", cx.progress_pct + "% of the way there");
    var detail = "Today about " + cx.current + "% of professional-services workers are under 25 — " +
      "roughly the same as before AI (2015–2019). The college hire becomes the exception once that " +
      "share is cut in half (to about " + Math.round(cx.threshold) + "%). We're " + cx.progress_pct + "% of the way there";
    detail += (cx.trajectory === "flat")
      ? ", and it hasn't started moving yet — so treat this as a projection of the current path, not a fixed date."
      : ".";
    set("inflection-detail", detail);
    // Progress bar width
    var bar = document.getElementById("inflection-bar-fill");
    if (bar) bar.style.width = Math.max(2, Math.min(100, cx.progress_pct)) + "%";
  }

  // ---- Timeline Chart ----
  var timelineChart = null;

  function renderTimeline(compositeData) {
    if (!compositeData || !compositeData.monthly || compositeData.monthly.length === 0) return;

    var ctx = document.getElementById("timeline-chart");
    if (!ctx) return;

    if (timelineChart) {
      timelineChart.destroy();
    }

    var sorted = compositeData.monthly.slice().sort(function(a, b) {
      return a.date.localeCompare(b.date);
    });

    var labels = sorted.map(function(d) { return d.date; });
    var scores = sorted.map(function(d) { return d.score; });
    var events = compositeData.events || [];

    // 6-month moving average trendline
    var trendWindow = 6;
    var trendline = scores.map(function(val, i) {
      if (i < trendWindow - 1) return null;
      var sum = 0;
      for (var j = i - trendWindow + 1; j <= i; j++) sum += scores[j];
      return Math.round(sum / trendWindow * 10) / 10;
    });

    // Build event point data.
    // - Two events sharing a date used to collide on eventLabelsMap; now we
    //   accumulate labels into an array and join with " · " in the tooltip.
    // - Events dated past the last available month (e.g. layoff
    //   announcements happening after the most recent BLS print) used to
    //   silently disappear because labels.indexOf(ev.date) returned -1.
    //   We snap those to the last label and prefix the rendered label with
    //   "(M)" so the reader knows the marker is anchored to the rightmost
    //   point rather than its true date.
    var lastLabel = labels[labels.length - 1];
    var eventLabelsMap = {};   // labelDate -> [string]
    var eventPositions = {};   // labelDate -> score y

    events.forEach(function(ev) {
      var targetLabel = ev.date;
      var idx = labels.indexOf(targetLabel);
      if (idx < 0) {
        if (ev.date > lastLabel) {
          targetLabel = lastLabel;
          idx = labels.length - 1;
        } else {
          // Event predates the series start — drop it
          return;
        }
      }
      var label = ev.label;
      if (targetLabel !== ev.date) {
        label = label + " (" + ev.date + ")";
      }
      if (!eventLabelsMap[targetLabel]) eventLabelsMap[targetLabel] = [];
      eventLabelsMap[targetLabel].push(label);
      eventPositions[targetLabel] = scores[idx];
    });

    var eventDataArr = labels.map(function(lbl) {
      return eventPositions[lbl] != null ? eventPositions[lbl] : null;
    });
    var eventLabelArr = labels.map(function(lbl) {
      return eventLabelsMap[lbl] ? eventLabelsMap[lbl].join(" · ") : null;
    });
    var eventRadiusArr = labels.map(function(lbl) {
      return eventPositions[lbl] != null ? 6 : 0;
    });

    timelineChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Displacement Score",
            data: scores,
            borderColor: "#58a6ff",
            backgroundColor: "rgba(88, 166, 255, 0.1)",
            borderWidth: 3,
            pointRadius: 0,
            pointHitRadius: 8,
            tension: 0.3,
            fill: true,
          },
          {
            label: "Trend (6mo avg)",
            data: trendline,
            borderColor: "#f0883e",
            borderWidth: 2,
            borderDash: [8, 4],
            pointRadius: 0,
            pointHitRadius: 0,
            tension: 0.4,
            fill: false,
            spanGaps: true,
          },
          {
            label: "Events",
            data: eventDataArr,
            borderColor: "transparent",
            backgroundColor: "#f0883e",
            pointRadius: eventRadiusArr,
            pointHoverRadius: 8,
            pointStyle: "circle",
            showLine: false,
            spanGaps: false,
            _eventLabels: eventLabelArr,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: "nearest",
            intersect: true,
            callbacks: {
              title: function(items) {
                return items[0].label;
              },
              label: function(context) {
                if (context.datasetIndex === 2 && context.parsed.y != null) {
                  var evLabels = context.dataset._eventLabels;
                  var evLabel = evLabels && evLabels[context.dataIndex];
                  return evLabel ? evLabel + " (" + context.parsed.y.toFixed(1) + ")" : "Score: " + context.parsed.y.toFixed(1);
                }
                if (context.datasetIndex === 1 && context.parsed.y != null) {
                  return "Trend: " + context.parsed.y.toFixed(1);
                }
                if (context.parsed.y != null) {
                  return "Score: " + context.parsed.y.toFixed(1);
                }
                return null;
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: false },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
            ticks: { maxTicksLimit: 8 },
          },
          y: {
            min: 0,
            max: 100,
            title: { display: true, text: "Displacement Score" },
            grid: { color: "rgba(48, 54, 61, 0.3)" },
            ticks: {
              stepSize: 25,
              callback: function(value) {
                var phaseLabels = { 0: "", 25: "Pre-disruption", 50: "Productivity", 75: "Erosion", 100: "Displacement" };
                return phaseLabels[value] !== undefined ? value + "  " + phaseLabels[value] : value;
              },
            },
          },
        },
        interaction: { mode: "nearest", intersect: false },
      },
      plugins: [{
        id: "phaseBands",
        beforeDraw: function(chart) {
          var yAxis = chart.scales.y;
          var xAxis = chart.scales.x;
          var ctxDraw = chart.ctx;

          var bands = [
            { min: 0, max: 25, color: "rgba(63, 185, 80, 0.05)" },
            { min: 25, max: 50, color: "rgba(88, 166, 255, 0.05)" },
            { min: 50, max: 75, color: "rgba(240, 136, 62, 0.05)" },
            { min: 75, max: 100, color: "rgba(248, 81, 73, 0.05)" },
          ];

          bands.forEach(function(band) {
            var yTop = yAxis.getPixelForValue(band.max);
            var yBottom = yAxis.getPixelForValue(band.min);
            ctxDraw.fillStyle = band.color;
            ctxDraw.fillRect(xAxis.left, yTop, xAxis.width, yBottom - yTop);
          });

          // Dashed lines at 25, 50, 75
          [25, 50, 75].forEach(function(val) {
            var yPos = yAxis.getPixelForValue(val);
            ctxDraw.save();
            ctxDraw.setLineDash([4, 4]);
            ctxDraw.strokeStyle = "rgba(139, 148, 158, 0.3)";
            ctxDraw.lineWidth = 1;
            ctxDraw.beginPath();
            ctxDraw.moveTo(xAxis.left, yPos);
            ctxDraw.lineTo(xAxis.right, yPos);
            ctxDraw.stroke();
            ctxDraw.restore();
          });
        },
      }],
    });

  }

  // ---- Expanded Regulatory Chart ----
  function renderExpandedRegulatory(regData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var regulators = regData.regulators || {};
    var regKeys = Object.keys(regulators);
    var colors = ["#58a6ff", "#3fb950", "#d2a8ff", "#f0883e", "#f85149", "#a371f7", "#d29922"];
    var bgColors = [
      "rgba(88,166,255,0.6)", "rgba(63,185,80,0.6)", "rgba(210,168,255,0.6)",
      "rgba(240,136,62,0.6)", "rgba(248,81,73,0.6)", "rgba(163,113,247,0.6)", "rgba(210,153,34,0.6)",
    ];

    // Collect all quarters
    var allQuarters = {};
    regKeys.forEach(function(key) {
      (regulators[key].quarterly || []).forEach(function(q) {
        allQuarters[q.quarter] = true;
      });
    });
    var quarters = Object.keys(allQuarters).sort();

    var datasets = regKeys.map(function(key, i) {
      var dataMap = {};
      (regulators[key].quarterly || []).forEach(function(q) {
        dataMap[q.quarter] = q.document_count;
      });
      return {
        label: regulators[key].name || key,
        data: quarters.map(function(q) { return dataMap[q] || 0; }),
        backgroundColor: bgColors[i % bgColors.length],
        borderColor: colors[i % colors.length],
        borderWidth: 1,
      };
    });

    state.expandedChart = new Chart(ctx, {
      type: "bar",
      data: { labels: quarters, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, padding: 12 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ": " + (ctx.parsed.y != null ? ctx.parsed.y : 0) + " docs";
              },
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            title: { display: true, text: "Quarter" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            stacked: true,
            title: { display: true, text: "Document Count" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  // ---- Card Rendering ----

  function renderCard(signal, summary) {
    var valEl = document.getElementById("val-" + signal);
    var changeEl = document.getElementById("change-" + signal);
    var updatedEl = document.getElementById("updated-" + signal);

    if (!summary) {
      valEl.textContent = "Data unavailable";
      valEl.style.fontSize = "1rem";
      valEl.style.color = "#8b949e";
      changeEl.textContent = "";
      updatedEl.textContent = "";
      return;
    }

    valEl.textContent = summary.formatted;
    var chg = changeArrow(summary.mom);
    changeEl.textContent = chg.arrow + " " + summary.momFormatted;
    changeEl.className = "card-change " + chg.cls;
    updatedEl.textContent = "Updated " + formatDate(summary.date);

    var sparkColor = "#58a6ff";
    if (signal === "employment") sparkColor = "#58a6ff";
    if (signal === "trends") sparkColor = "#d2a8ff";
    if (signal === "github") sparkColor = "#3fb950";
    if (signal === "earnings") sparkColor = "#f0883e";
    if (signal === "workforce") sparkColor = "#f85149";
    if (signal === "vc") sparkColor = "#a371f7";
    if (signal === "jobs") sparkColor = "#d2a8ff";
    if (signal === "youth") sparkColor = "#f0883e";
    if (signal === "regulatory") sparkColor = "#f0883e";

    createSparkline(
      "spark-" + signal,
      summary.sparkLabels,
      summary.sparkData,
      sparkColor
    );
  }

  // ---- Expanded Chart Rendering ----

  function renderExpandedEmployment(empData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var seriesKeys = empData.series ? Object.keys(empData.series) : [];
    var colors = ["#58a6ff", "#3fb950", "#d2a8ff", "#f0883e", "#f85149"];
    var datasets = [];

    seriesKeys.forEach(function (key, i) {
      var s = empData.series[key];
      var sorted = (s.data || []).slice().sort(function (a, b) {
        return a.date.localeCompare(b.date);
      });
      datasets.push({
        label: s.name || key,
        data: sorted.map(function (d) { return { x: d.date, y: d.value }; }),
        borderColor: colors[i % colors.length],
        backgroundColor: "transparent",
        borderWidth: key === "CES6000000001" ? 3 : 1.5,
        pointRadius: 2,
        tension: 0.3,
      });
    });

    state.expandedChart = new Chart(ctx, {
      type: "line",
      data: { datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, pointStyle: "line", padding: 16 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ": " + formatNumber(ctx.parsed.y) + "K";
              },
            },
          },
        },
        scales: {
          x: {
            type: "category",
            labels: getAllDates(empData.series),
            title: { display: true, text: "Month" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            title: { display: true, text: "Employment (thousands)" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function getAllDates(seriesObj) {
    var dateSet = {};
    Object.keys(seriesObj).forEach(function (key) {
      (seriesObj[key].data || []).forEach(function (d) {
        dateSet[d.date] = true;
      });
    });
    return Object.keys(dateSet).sort();
  }

  function renderExpandedTrends(trendsData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var categories = trendsData.categories;
    var catKeys = Object.keys(categories);
    var colors = ["#d2a8ff", "#58a6ff", "#3fb950", "#f0883e"];
    var datasets = [];

    // Collect all dates
    var allDates = {};
    catKeys.forEach(function (key) {
      var catData = categories[key].composite || categories[key].data || categories[key];
      if (Array.isArray(catData)) {
        catData.forEach(function (d) { allDates[d.date] = true; });
      }
    });
    var dates = Object.keys(allDates).sort();

    catKeys.forEach(function (key, i) {
      var catData = categories[key].composite || categories[key].data || categories[key];
      var dataMap = {};
      if (Array.isArray(catData)) {
        catData.forEach(function (d) { dataMap[d.date] = d.value; });
      }
      datasets.push({
        label: key,
        data: dates.map(function (d) { return dataMap[d] || null; }),
        borderColor: colors[i % colors.length],
        backgroundColor: "transparent",
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.3,
        spanGaps: true,
      });
    });

    state.expandedChart = new Chart(ctx, {
      type: "line",
      data: { labels: dates, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, pointStyle: "line", padding: 16 },
          },
          tooltip: { mode: "index", intersect: false },
        },
        scales: {
          x: {
            title: { display: true, text: "Month" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            title: { display: true, text: "Search Interest Index" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
            min: 0,
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedGithub(ghData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var monthly = ghData.monthly || ghData.aggregate || [];
    var sorted = monthly.slice().sort(function (a, b) {
      return a.date.localeCompare(b.date);
    });

    var reposKey = sorted.length > 0 && sorted[0].new_repos != null ? "new_repos" : "total_new_repos";
    var starsKey = sorted.length > 0 && sorted[0].cumulative_stars != null ? "cumulative_stars" : "total_stars";
    var labels = sorted.map(function (d) { return d.date; });
    var newRepos = sorted.map(function (d) { return d[reposKey]; });
    var cumStars = sorted.map(function (d) { return d[starsKey]; });

    state.expandedChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            type: "bar",
            label: "New Repos",
            data: newRepos,
            backgroundColor: "rgba(63, 185, 80, 0.5)",
            borderColor: "#3fb950",
            borderWidth: 1,
            yAxisID: "y",
            order: 2,
          },
          {
            type: "line",
            label: "Cumulative Stars",
            data: cumStars,
            borderColor: "#58a6ff",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.3,
            yAxisID: "y1",
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, padding: 16 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function (ctx) {
                if (ctx.dataset.label === "Cumulative Stars") {
                  return ctx.dataset.label + ": " + formatStars(ctx.parsed.y);
                }
                return ctx.dataset.label + ": " + ctx.parsed.y;
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Month" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            type: "linear",
            position: "left",
            title: { display: true, text: "New Repos" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y1: {
            type: "linear",
            position: "right",
            title: { display: true, text: "Cumulative Stars" },
            grid: { drawOnChartArea: false },
            ticks: {
              callback: function (value) { return formatStars(value); },
            },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedEarnings(earningsData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var firms = earningsData.firms || {};
    var firmKeys = Object.keys(firms);
    var colors = ["#58a6ff", "#3fb950", "#d2a8ff", "#f0883e", "#f85149", "#79c0ff", "#d29922", "#a5d6ff"];
    var datasets = [];
    var allQuarters = {};

    firmKeys.forEach(function(key, i) {
      var firm = firms[key];
      var quarterly = (firm.quarterly || []).slice().sort(function(a, b) {
        return a.quarter.localeCompare(b.quarter);
      });
      quarterly.forEach(function(q) { allQuarters[q.quarter] = true; });
      var dataMap = {};
      quarterly.forEach(function(q) { dataMap[q.quarter] = q.ai_revenue_mm; });

      datasets.push({
        label: firm.name || key,
        data: [], // will be filled after we know all quarters
        borderColor: colors[i % colors.length],
        backgroundColor: "transparent",
        borderWidth: 2,
        pointRadius: 2,
        tension: 0.3,
        spanGaps: true,
        _dataMap: dataMap,
      });
    });

    var quarters = Object.keys(allQuarters).sort();
    datasets.forEach(function(ds) {
      ds.data = quarters.map(function(q) { return ds._dataMap[q] || null; });
      delete ds._dataMap;
    });

    state.expandedChart = new Chart(ctx, {
      type: "line",
      data: { labels: quarters, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, pointStyle: "line", padding: 16 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ": $" + (ctx.parsed.y != null ? ctx.parsed.y : "--") + "M";
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Quarter" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            title: { display: true, text: "AI Revenue ($M)" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedWorkforce(earningsData, workforceData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    // Headcount bars from workforce aggregate (annual)
    var wfAgg = (workforceData && workforceData.aggregate) || [];
    var wfSorted = wfAgg.slice().sort(function(a, b) { return a.year - b.year; });
    var headcountLabels = wfSorted.map(function(d) { return String(d.year); });
    var headcountData = wfSorted.map(function(d) { return d.total_headcount; });

    // Rev per employee line from earnings aggregate (quarterly)
    var eAgg = (earningsData && earningsData.aggregate) || [];
    var eSorted = eAgg.slice().sort(function(a, b) { return a.quarter.localeCompare(b.quarter); });
    var rpeLabels = eSorted.map(function(d) { return d.quarter; });
    var rpeData = eSorted.map(function(d) { return d.avg_rev_per_employee; });

    // Merge all labels (years + quarters) in order
    var allLabels = [];
    var labelSet = {};
    headcountLabels.concat(rpeLabels).forEach(function(l) {
      if (!labelSet[l]) { allLabels.push(l); labelSet[l] = true; }
    });
    allLabels.sort();

    // Map data to merged labels
    var hcMap = {};
    wfSorted.forEach(function(d) { hcMap[String(d.year)] = d.total_headcount; });
    var rpeMap = {};
    eSorted.forEach(function(d) { rpeMap[d.quarter] = d.avg_rev_per_employee; });

    state.expandedChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: allLabels,
        datasets: [
          {
            type: "bar",
            label: "Headcount",
            data: allLabels.map(function(l) { return hcMap[l] || null; }),
            backgroundColor: "rgba(88, 166, 255, 0.4)",
            borderColor: "#58a6ff",
            borderWidth: 1,
            yAxisID: "y",
            order: 2,
          },
          {
            type: "line",
            label: "Rev/Employee ($K)",
            data: allLabels.map(function(l) { return rpeMap[l] || null; }),
            borderColor: "#f85149",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.3,
            yAxisID: "y1",
            order: 1,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, padding: 16 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function(ctx) {
                if (ctx.dataset.label === "Headcount") {
                  return ctx.dataset.label + ": " + formatNumber(ctx.parsed.y);
                }
                return ctx.dataset.label + ": $" + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) : "--") + "K";
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Period" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Headcount" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
            ticks: {
              callback: function(value) { return formatCompact(value); },
            },
          },
          y1: {
            type: "linear",
            position: "right",
            title: { display: true, text: "Rev/Employee ($K)" },
            grid: { drawOnChartArea: false },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedVc(vcData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var categories = vcData.categories || {};
    var catKeys = Object.keys(categories);
    var colors = ["#58a6ff", "#3fb950", "#d2a8ff", "#f0883e", "#f85149", "#a371f7"];
    var bgColors = ["rgba(88,166,255,0.6)", "rgba(63,185,80,0.6)", "rgba(210,168,255,0.6)", "rgba(240,136,62,0.6)", "rgba(248,81,73,0.6)", "rgba(163,113,247,0.6)"];

    // Collect all quarters
    var allQuarters = {};
    catKeys.forEach(function(key) {
      (categories[key].quarterly || []).forEach(function(q) {
        allQuarters[q.quarter] = true;
      });
    });
    var quarters = Object.keys(allQuarters).sort();

    var datasets = catKeys.map(function(key, i) {
      var dataMap = {};
      (categories[key].quarterly || []).forEach(function(q) {
        dataMap[q.quarter] = q.funding_mm;
      });
      return {
        label: categories[key].name || key,
        data: quarters.map(function(q) { return dataMap[q] || 0; }),
        backgroundColor: bgColors[i % bgColors.length],
        borderColor: colors[i % colors.length],
        borderWidth: 1,
      };
    });

    state.expandedChart = new Chart(ctx, {
      type: "bar",
      data: { labels: quarters, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, padding: 12 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ": $" + (ctx.parsed.y != null ? ctx.parsed.y : 0) + "M";
              },
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            title: { display: true, text: "Quarter" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            stacked: true,
            title: { display: true, text: "Funding ($ millions)" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedJobs(jobsData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var monthly = (jobsData.monthly || []).slice().sort(function(a, b) {
      return a.date.localeCompare(b.date);
    });

    var labels = monthly.map(function(d) { return d.date; });
    var aiPct = monthly.map(function(d) { return d.ai_postings_pct; });
    var tradPct = monthly.map(function(d) { return d.traditional_pct; });

    state.expandedChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "AI Postings %",
            data: aiPct,
            borderColor: "#3fb950",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.3,
            yAxisID: "y",
          },
          {
            label: "Traditional Postings %",
            data: tradPct,
            borderColor: "#f85149",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.3,
            yAxisID: "y",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: { usePointStyle: true, pointStyle: "line", padding: 16 },
          },
          tooltip: {
            mode: "index",
            intersect: false,
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ": " + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) : "--") + "%";
              },
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Month" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
          y: {
            title: { display: true, text: "Percentage of Postings (%)" },
            grid: { color: "rgba(48, 54, 61, 0.5)" },
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedYouth(youthData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();
    var rows = (youthData.monthly || []).slice().sort(function (a, b) { return a.date.localeCompare(b.date); });
    var labels = rows.map(function (d) { return d.date.slice(0, 4); });
    var u25 = rows.map(function (d) { return d.youth_share_u25 != null ? d.youth_share_u25 * 100 : null; });
    var u35 = rows.map(function (d) { return d.youth_share_u35 != null ? d.youth_share_u35 * 100 : null; });
    var base = rows.filter(function (d) { var y = d.date.slice(0, 4); return y >= "2015" && y <= "2019"; })
      .map(function (d) { return d.youth_share_u25 * 100; });
    var baseline = base.length ? base.reduce(function (a, b) { return a + b; }, 0) / base.length : null;
    var threshold = baseline != null ? baseline * 0.5 : null;
    state.expandedChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          { label: "Under 25 (%)", data: u25, borderColor: "#f0883e", backgroundColor: "transparent", borderWidth: 2, pointRadius: 3, tension: 0.3 },
          { label: "Under 35 (%)", data: u35, borderColor: "#58a6ff", backgroundColor: "transparent", borderWidth: 2, pointRadius: 3, tension: 0.3 },
          { label: "Crossover (50% of baseline)", data: labels.map(function () { return threshold; }), borderColor: "#f85149", borderDash: [6, 4], backgroundColor: "transparent", borderWidth: 1.5, pointRadius: 0 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: "top", labels: { usePointStyle: true, pointStyle: "line", padding: 16 } },
          tooltip: { mode: "index", intersect: false, callbacks: { label: function (ctx) { return ctx.dataset.label + ": " + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) : "--") + "%"; } } },
        },
        scales: {
          x: { title: { display: true, text: "Year" }, grid: { color: "rgba(48, 54, 61, 0.5)" } },
          y: { title: { display: true, text: "Share of professional-services workforce (%)" }, grid: { color: "rgba(48, 54, 61, 0.5)" } },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  // ---- Expand / Collapse ----

  function expandSignal(signal) {
    var section = document.getElementById("expanded-section");
    var titleEl = document.getElementById("expanded-title");

    // If same card clicked, collapse
    if (state.expandedSignal === signal) {
      collapseExpanded();
      return;
    }

    // Remove active from all cards
    document.querySelectorAll(".card").forEach(function (c) {
      c.classList.remove("active");
    });

    // Set active on clicked card
    var card = document.getElementById("card-" + signal);
    if (card) card.classList.add("active");

    state.expandedSignal = signal;
    section.hidden = false;

    var titles = {
      employment: "Professional Services Employment (BLS)",
      trends: "AI Search Interest (Google Trends)",
      github: "Open Source AI Activity (GitHub)",
      earnings: "AI Revenue Reporting (SEC/Earnings)",
      workforce: "Revenue Per Employee (SEC 10-K)",
      vc: "VC Funding: AI Services (SEC Form D)",
      jobs: "Professional-Services Hiring (BLS JOLTS)",
      youth: "Apprenticeship Pipeline — Youth Share (Census ACS)",
      regulatory: "Regulatory Guidance (Fed / OCC / SEC / EU / NIST)",
    };
    titleEl.textContent = titles[signal] || signal;

    // Render appropriate expanded chart
    var data = state.data[signal];
    if (!data) return;

    if (signal === "employment") renderExpandedEmployment(data);
    else if (signal === "trends") renderExpandedTrends(data);
    else if (signal === "github") renderExpandedGithub(data);
    else if (signal === "earnings") renderExpandedEarnings(data);
    else if (signal === "workforce") renderExpandedWorkforce(state.data.earnings, state.data.workforce);
    else if (signal === "vc") renderExpandedVc(data);
    else if (signal === "jobs") renderExpandedJobs(data);
    else if (signal === "youth") renderExpandedYouth(data);
    else if (signal === "regulatory") renderExpandedRegulatory(data);

    // Scroll to expanded section
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function collapseExpanded() {
    var section = document.getElementById("expanded-section");
    section.hidden = true;
    state.expandedSignal = null;
    if (state.expandedChart) {
      state.expandedChart.destroy();
      state.expandedChart = null;
    }
    document.querySelectorAll(".card").forEach(function (c) {
      c.classList.remove("active");
    });
  }

  // ---- Data Loading ----

  function fetchJSON(url) {
    return fetch(url)
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
      });
  }

  function loadData() {
    var promises = [
      fetchJSON(DATA_PATHS.employment).catch(function () { console.warn("Employment data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.trends).catch(function () { console.warn("Trends data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.github).catch(function () { console.warn("GitHub data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.earnings).catch(function () { console.warn("Earnings data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.workforce).catch(function () { console.warn("Workforce data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.vc).catch(function () { console.warn("VC funding data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.jobs).catch(function () { console.warn("Jobs data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.regulatory).catch(function () { console.warn("Regulatory data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.composite).catch(function () { console.warn("Composite data unavailable; signal will show no data."); return null; }),
      fetchJSON(DATA_PATHS.inflection).catch(function () { console.warn("Inflection data unavailable; panel will hide."); return null; }),
      fetchJSON(DATA_PATHS.youth).catch(function () { console.warn("Youth-share data unavailable; card will show no data."); return null; }),
    ];

    Promise.all(promises).then(function (results) {
      state.data.employment = results[0];
      state.data.trends = results[1];
      state.data.github = results[2];
      state.data.earnings = results[3];
      state.data.workforce = results[4];
      state.data.vc = results[5];
      state.data.jobs = results[6];
      state.data.regulatory = results[7];
      state.data.composite = results[8];
      state.data.inflection = results[9];
      state.data.youth = results[10];
      render();
    });
  }

  // ---- Render All ----

  function render() {
    // Update last-updated from metadata
    var dates = [];
    ["employment", "trends", "github", "earnings", "workforce", "vc", "jobs", "regulatory"].forEach(function (key) {
      var d = state.data[key];
      if (d && d.metadata && d.metadata.last_updated) {
        dates.push(d.metadata.last_updated);
      }
    });
    if (dates.length > 0) {
      dates.sort();
      var mostRecent = dates[dates.length - 1];
      document.getElementById("last-updated").textContent =
        "Last updated: " + formatDate(mostRecent);
    }

    // Hero composite score
    renderHeroScore(state.data.composite);
    renderInflection(state.data.inflection);
    renderTimeline(state.data.composite);

    // Render cards
    var empSummary = getEmploymentSummary(state.data.employment);
    renderCard("employment", empSummary);

    var trendsSummary = getTrendsSummary(state.data.trends);
    renderCard("trends", trendsSummary);

    var earningsSummary = getEarningsSummary(state.data.earnings);
    renderCard("earnings", earningsSummary);

    var workforceSummary = getWorkforceSummary(state.data.earnings);
    renderCard("workforce", workforceSummary);

    renderCard("youth", getYouthSummary(state.data.youth));

    var vcSummary = getVcSummary(state.data.vc);
    renderCard("vc", vcSummary);

    var jobsSummary = getJobsSummary(state.data.jobs);
    renderCard("jobs", jobsSummary);

    // GitHub + Regulatory cards removed from the dashboard (signals still feed the
    // composite via the Python normalizer — dropping the card != dropping the data).
  }

  // ---- Event Binding ----

  function bindEvents() {
    // Card clicks
    document.querySelectorAll(".card").forEach(function (card) {
      card.addEventListener("click", function () {
        var signal = card.getAttribute("data-signal");
        if (signal) expandSignal(signal);
      });
    });

    // Close button
    var closeBtn = document.getElementById("expanded-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        collapseExpanded();
      });
    }

    // Keyboard: Escape to close expanded
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && state.expandedSignal) {
        collapseExpanded();
      }
    });
  }

  // ---- Init ----

  function init() {
    setChartDefaults();
    bindEvents();
    loadData();
  }

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
