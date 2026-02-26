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
  };

  // ---- Fallback sample data ----
  // Used when fetch fails (dev/offline). First/last 3 points per signal.
  const FALLBACK = {
    employment: {
      metadata: {
        source: "BLS",
        last_updated: "2025-12-01",
        series_id: "CES5000000001",
      },
      series: {
        CES5000000001: {
          name: "Professional and Business Services",
          data: [
            { date: "2022-11", value: 22872 },
            { date: "2022-12", value: 22911 },
            { date: "2023-01", value: 22943 },
            { date: "2023-02", value: 22980 },
            { date: "2023-03", value: 22998 },
            { date: "2023-04", value: 23010 },
            { date: "2023-05", value: 23020 },
            { date: "2023-06", value: 23048 },
            { date: "2023-07", value: 23060 },
            { date: "2023-08", value: 23075 },
            { date: "2023-09", value: 23088 },
            { date: "2023-10", value: 23100 },
            { date: "2023-11", value: 23105 },
            { date: "2023-12", value: 23110 },
            { date: "2024-01", value: 23090 },
            { date: "2024-02", value: 23070 },
            { date: "2024-03", value: 23085 },
            { date: "2024-04", value: 23095 },
            { date: "2024-05", value: 23100 },
            { date: "2024-06", value: 23110 },
            { date: "2024-07", value: 23120 },
            { date: "2024-08", value: 23130 },
            { date: "2024-09", value: 23140 },
            { date: "2024-10", value: 23148 },
            { date: "2024-11", value: 23142 },
            { date: "2024-12", value: 23150 },
          ],
        },
        CES5051000001: {
          name: "Professional, Scientific, and Technical Services",
          data: [
            { date: "2022-11", value: 10200 },
            { date: "2023-06", value: 10350 },
            { date: "2024-12", value: 10520 },
          ],
        },
        CES5054100001: {
          name: "Computer Systems Design",
          data: [
            { date: "2022-11", value: 2180 },
            { date: "2023-06", value: 2210 },
            { date: "2024-12", value: 2240 },
          ],
        },
        CES5054000001: {
          name: "Computer and Mathematical Occupations",
          data: [
            { date: "2022-11", value: 2000 },
            { date: "2023-06", value: 2025 },
            { date: "2024-12", value: 2048 },
          ],
        },
        CES5056000001: {
          name: "Administrative and Support Services",
          data: [
            { date: "2022-11", value: 8900 },
            { date: "2023-06", value: 8950 },
            { date: "2024-12", value: 8980 },
          ],
        },
      },
    },
    trends: {
      metadata: {
        source: "Google Trends",
        last_updated: "2025-12-15",
      },
      categories: {
        "ai coding tools": {
          data: [
            { date: "2022-11", value: 12 },
            { date: "2022-12", value: 18 },
            { date: "2023-01", value: 25 },
            { date: "2023-02", value: 30 },
            { date: "2023-03", value: 33 },
            { date: "2023-04", value: 35 },
            { date: "2023-05", value: 38 },
            { date: "2023-06", value: 40 },
            { date: "2023-07", value: 42 },
            { date: "2023-08", value: 44 },
            { date: "2023-09", value: 47 },
            { date: "2023-10", value: 50 },
            { date: "2023-11", value: 52 },
            { date: "2023-12", value: 55 },
            { date: "2024-01", value: 58 },
            { date: "2024-02", value: 60 },
            { date: "2024-03", value: 62 },
            { date: "2024-04", value: 63 },
            { date: "2024-05", value: 65 },
            { date: "2024-06", value: 68 },
            { date: "2024-07", value: 70 },
            { date: "2024-08", value: 72 },
            { date: "2024-09", value: 75 },
            { date: "2024-10", value: 78 },
            { date: "2024-11", value: 80 },
            { date: "2024-12", value: 82 },
          ],
        },
        "ai replacing jobs": {
          data: [
            { date: "2022-11", value: 8 },
            { date: "2022-12", value: 15 },
            { date: "2023-01", value: 45 },
            { date: "2023-02", value: 55 },
            { date: "2023-03", value: 48 },
            { date: "2023-04", value: 42 },
            { date: "2023-05", value: 38 },
            { date: "2023-06", value: 35 },
            { date: "2023-07", value: 33 },
            { date: "2023-08", value: 32 },
            { date: "2023-09", value: 34 },
            { date: "2023-10", value: 36 },
            { date: "2023-11", value: 38 },
            { date: "2023-12", value: 40 },
            { date: "2024-01", value: 42 },
            { date: "2024-02", value: 44 },
            { date: "2024-03", value: 48 },
            { date: "2024-04", value: 50 },
            { date: "2024-05", value: 52 },
            { date: "2024-06", value: 55 },
            { date: "2024-07", value: 58 },
            { date: "2024-08", value: 60 },
            { date: "2024-09", value: 62 },
            { date: "2024-10", value: 65 },
            { date: "2024-11", value: 68 },
            { date: "2024-12", value: 70 },
          ],
        },
        "chatgpt alternatives": {
          data: [
            { date: "2022-11", value: 0 },
            { date: "2022-12", value: 5 },
            { date: "2023-01", value: 60 },
            { date: "2023-02", value: 72 },
            { date: "2023-03", value: 55 },
            { date: "2023-04", value: 45 },
            { date: "2023-05", value: 40 },
            { date: "2023-06", value: 38 },
            { date: "2023-07", value: 36 },
            { date: "2023-08", value: 35 },
            { date: "2023-09", value: 34 },
            { date: "2023-10", value: 33 },
            { date: "2023-11", value: 35 },
            { date: "2023-12", value: 38 },
            { date: "2024-01", value: 40 },
            { date: "2024-02", value: 42 },
            { date: "2024-03", value: 44 },
            { date: "2024-04", value: 45 },
            { date: "2024-05", value: 48 },
            { date: "2024-06", value: 50 },
            { date: "2024-07", value: 52 },
            { date: "2024-08", value: 55 },
            { date: "2024-09", value: 58 },
            { date: "2024-10", value: 60 },
            { date: "2024-11", value: 62 },
            { date: "2024-12", value: 64 },
          ],
        },
        "ai automation": {
          data: [
            { date: "2022-11", value: 15 },
            { date: "2022-12", value: 20 },
            { date: "2023-01", value: 35 },
            { date: "2023-02", value: 40 },
            { date: "2023-03", value: 38 },
            { date: "2023-04", value: 36 },
            { date: "2023-05", value: 35 },
            { date: "2023-06", value: 34 },
            { date: "2023-07", value: 33 },
            { date: "2023-08", value: 34 },
            { date: "2023-09", value: 36 },
            { date: "2023-10", value: 38 },
            { date: "2023-11", value: 40 },
            { date: "2023-12", value: 42 },
            { date: "2024-01", value: 44 },
            { date: "2024-02", value: 46 },
            { date: "2024-03", value: 48 },
            { date: "2024-04", value: 50 },
            { date: "2024-05", value: 52 },
            { date: "2024-06", value: 55 },
            { date: "2024-07", value: 58 },
            { date: "2024-08", value: 60 },
            { date: "2024-09", value: 62 },
            { date: "2024-10", value: 65 },
            { date: "2024-11", value: 68 },
            { date: "2024-12", value: 72 },
          ],
        },
      },
    },
    github: {
      metadata: {
        source: "GitHub",
        last_updated: "2025-12-20",
      },
      monthly: [
        { date: "2022-11", new_repos: 120, cumulative_stars: 45000 },
        { date: "2022-12", new_repos: 180, cumulative_stars: 52000 },
        { date: "2023-01", new_repos: 310, cumulative_stars: 68000 },
        { date: "2023-02", new_repos: 350, cumulative_stars: 78000 },
        { date: "2023-03", new_repos: 380, cumulative_stars: 88000 },
        { date: "2023-04", new_repos: 360, cumulative_stars: 96000 },
        { date: "2023-05", new_repos: 340, cumulative_stars: 103000 },
        { date: "2023-06", new_repos: 320, cumulative_stars: 110000 },
        { date: "2023-07", new_repos: 330, cumulative_stars: 116000 },
        { date: "2023-08", new_repos: 340, cumulative_stars: 122000 },
        { date: "2023-09", new_repos: 355, cumulative_stars: 128000 },
        { date: "2023-10", new_repos: 370, cumulative_stars: 134000 },
        { date: "2023-11", new_repos: 390, cumulative_stars: 140000 },
        { date: "2023-12", new_repos: 410, cumulative_stars: 146000 },
        { date: "2024-01", new_repos: 430, cumulative_stars: 152000 },
        { date: "2024-02", new_repos: 445, cumulative_stars: 157000 },
        { date: "2024-03", new_repos: 460, cumulative_stars: 162000 },
        { date: "2024-04", new_repos: 450, cumulative_stars: 166000 },
        { date: "2024-05", new_repos: 465, cumulative_stars: 170000 },
        { date: "2024-06", new_repos: 480, cumulative_stars: 174000 },
        { date: "2024-07", new_repos: 490, cumulative_stars: 178000 },
        { date: "2024-08", new_repos: 500, cumulative_stars: 182000 },
        { date: "2024-09", new_repos: 510, cumulative_stars: 186000 },
        { date: "2024-10", new_repos: 520, cumulative_stars: 190000 },
        { date: "2024-11", new_repos: 505, cumulative_stars: 194000 },
        { date: "2024-12", new_repos: 515, cumulative_stars: 198000 },
      ],
    },
  };

  // ---- State ----
  let state = {
    data: { employment: null, trends: null, github: null },
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
    // Primary series: CES5000000001 (Professional & Business Services total)
    var primaryKey = "CES5000000001";
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
      var catData = categories[key].data || categories[key];
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
    if (!ghData || !ghData.monthly || ghData.monthly.length === 0) return null;

    var sorted = ghData.monthly.slice().sort(function (a, b) {
      return a.date.localeCompare(b.date);
    });

    var trailing12 = last(sorted, 12);
    var latest = sorted[sorted.length - 1];
    var prev = sorted.length >= 2 ? sorted[sorted.length - 2] : null;
    var momRepos = prev ? latest.new_repos - prev.new_repos : 0;

    return {
      value: latest.cumulative_stars,
      formatted: formatStars(latest.cumulative_stars) + " \u2605",
      mom: momRepos,
      momFormatted: (momRepos >= 0 ? "+" : "") + momRepos + " repos",
      date: latest.date,
      sparkLabels: trailing12.map(function (d) { return d.date; }),
      sparkData: trailing12.map(function (d) { return d.cumulative_stars; }),
    };
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
    changeEl.textContent = chg.arrow + " " + summary.momFormatted + " MoM";
    changeEl.className = "card-change " + chg.cls;
    updatedEl.textContent = "Updated " + formatDate(summary.date);

    var sparkColor = "#58a6ff";
    if (signal === "employment") sparkColor = "#58a6ff";
    if (signal === "trends") sparkColor = "#d2a8ff";
    if (signal === "github") sparkColor = "#3fb950";

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
        borderWidth: key === "CES5000000001" ? 3 : 1.5,
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
      var catData = categories[key].data || categories[key];
      if (Array.isArray(catData)) {
        catData.forEach(function (d) { allDates[d.date] = true; });
      }
    });
    var dates = Object.keys(allDates).sort();

    catKeys.forEach(function (key, i) {
      var catData = categories[key].data || categories[key];
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
            max: 100,
          },
        },
        interaction: { mode: "index", intersect: false },
      },
    });
  }

  function renderExpandedGithub(ghData) {
    var ctx = document.getElementById("expanded-chart");
    if (state.expandedChart) state.expandedChart.destroy();

    var sorted = (ghData.monthly || []).slice().sort(function (a, b) {
      return a.date.localeCompare(b.date);
    });

    var labels = sorted.map(function (d) { return d.date; });
    var newRepos = sorted.map(function (d) { return d.new_repos; });
    var cumStars = sorted.map(function (d) { return d.cumulative_stars; });

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
    };
    titleEl.textContent = titles[signal] || signal;

    // Render appropriate expanded chart
    var data = state.data[signal];
    if (!data) return;

    if (signal === "employment") renderExpandedEmployment(data);
    else if (signal === "trends") renderExpandedTrends(data);
    else if (signal === "github") renderExpandedGithub(data);

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
      fetchJSON(DATA_PATHS.employment).catch(function () {
        console.warn("Employment data fetch failed, using fallback.");
        return FALLBACK.employment;
      }),
      fetchJSON(DATA_PATHS.trends).catch(function () {
        console.warn("Trends data fetch failed, using fallback.");
        return FALLBACK.trends;
      }),
      fetchJSON(DATA_PATHS.github).catch(function () {
        console.warn("GitHub data fetch failed, using fallback.");
        return FALLBACK.github;
      }),
    ];

    Promise.all(promises).then(function (results) {
      state.data.employment = results[0];
      state.data.trends = results[1];
      state.data.github = results[2];
      render();
    });
  }

  // ---- Render All ----

  function render() {
    // Update last-updated from metadata
    var dates = [];
    ["employment", "trends", "github"].forEach(function (key) {
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

    // Render cards
    var empSummary = getEmploymentSummary(state.data.employment);
    renderCard("employment", empSummary);

    var trendsSummary = getTrendsSummary(state.data.trends);
    renderCard("trends", trendsSummary);

    var ghSummary = getGithubSummary(state.data.github);
    renderCard("github", ghSummary);
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
