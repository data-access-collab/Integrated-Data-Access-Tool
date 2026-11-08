import Alpine from "alpinejs";

import countrySelect from "./components/country_select";
import dateField from "./components/date_field";
import plainFile from "./components/plain_file";

window.Alpine = Alpine;
Alpine.data("countrySelect", countrySelect);
Alpine.data("dateField", dateField);
Alpine.data("plainFile", plainFile);
Alpine.start();

/* Messages close button */
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-dismiss-alert]");
  if (btn) btn.closest("[role=alert]").remove();
});
