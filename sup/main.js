// ========== THEME TOGGLE ==========
const themeToggle = document.getElementById("theme-toggle");
const body = document.body;

if (
  localStorage.getItem("theme") === "dark" ||
  (!localStorage.getItem("theme") &&
    window.matchMedia("(prefers-color-scheme: dark)").matches)
) {
  body.classList.add("dark");
  if (themeToggle) themeToggle.textContent = "☀️";
}

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    body.classList.toggle("dark");
    const dark = body.classList.contains("dark");
    localStorage.setItem("theme", dark ? "dark" : "light");
    themeToggle.textContent = dark ? "☀️" : "🌙";
  });
}

// ========== DASHBOARD SIM ==========
const hr = document.getElementById("hr");
const temp = document.getElementById("temp");
const alerts = document.getElementById("alerts");
if (hr && temp && alerts) {
  setInterval(() => {
    hr.textContent = `${Math.floor(70 + Math.random() * 20)} bpm`;
    temp.textContent = `${(33 + Math.random() * 2).toFixed(1)} °C`;
    alerts.textContent = Math.floor(Math.random() * 3);
    document.querySelectorAll(".metric").forEach(m => {
      m.style.boxShadow = `0 0 20px rgba(0,217,255,${0.3 + Math.random() * 0.2})`;
    });
  }, 1800);
}

// ========== FORM SUBMIT ==========
const contactForm = document.getElementById("contactForm");
if (contactForm) {
  contactForm.addEventListener("submit", (e) => {
    e.preventDefault();
    alert("✅ Thank you for reaching out! We’ll contact you soon.");
    contactForm.reset();
  });
}

// ========== FLOATING ABOUT CARD MOTION ==========
document.querySelectorAll(".about-card").forEach(card => {
  card.addEventListener("mousemove", e => {
    const { offsetX, offsetY } = e;
    const { offsetWidth, offsetHeight } = card;
    const rotateX = ((offsetY / offsetHeight) - 0.5) * 10;
    const rotateY = ((offsetX / offsetWidth) - 0.5) * -10;
    card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  });
  card.addEventListener("mouseleave", () => {
    card.style.transform = "rotateX(0deg) rotateY(0deg)";
  });
});

// ========== SCROLL FADE ==========
window.addEventListener("scroll", () => {
  document.querySelectorAll("section").forEach(sec => {
    const top = sec.getBoundingClientRect().top;
    if (top < window.innerHeight - 80) sec.style.opacity = 1;
  });
});
