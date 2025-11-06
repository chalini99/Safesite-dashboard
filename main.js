document.addEventListener("DOMContentLoaded", () => {
  const runBtn = document.getElementById("runAI");
  const status = document.getElementById("aiStatus");
  const liveData = document.getElementById("liveData");
  const tempSpan = document.getElementById("temp");
  const gasSpan = document.getElementById("gas");
  const helmetSpan = document.getElementById("helmet");

  if (runBtn) {
    runBtn.addEventListener("click", async () => {
      status.textContent = "🚀 Running AI Detection...";
      try {
        const res = await fetch("http://127.0.0.1:5001/run_ai");
        const data = await res.json();
        if (data.status === "success") {
          const violations = data.data.helmet_violations;
          status.textContent = `✅ Detection Complete! Helmet Violations: ${violations}`;
        } else {
          status.textContent = `❌ Error: ${data.message}`;
        }
      } catch (err) {
        status.textContent = "⚠️ Cannot connect to backend.";
      }
    });
  }

  async function refreshData() {
    try {
      const res = await fetch("http://127.0.0.1:5001/get_data");
      const data = await res.json();
      liveData.textContent = `🌡️ Temp: ${data.temperature} °C | 🧪 Gas: ${data.gas_level} ppm | ⛑️ Helmet Violations: ${data.helmet_violations}`;
      tempSpan.textContent = `${data.temperature} °C`;
      gasSpan.textContent = `${data.gas_level} ppm`;
      helmetSpan.textContent = `${data.helmet_violations}`;
    } catch (err) {
      liveData.textContent = "No live data available.";
    }
  }

  setInterval(refreshData, 5000);
  refreshData();
});
