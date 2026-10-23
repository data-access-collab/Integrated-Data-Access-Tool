import Alpine from "alpinejs";

window.Alpine = Alpine;
Alpine.start();

/* Messages close button */
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-dismiss-alert]");
  if (btn) btn.closest("[role=alert]").remove();
});
