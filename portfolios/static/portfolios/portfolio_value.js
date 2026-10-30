"use strict";

const refreshButton = document.querySelector("#refresh-portfolio-value");
const portfolioValue = document.querySelector("#portfolio-value");
const portfolioValueStatus = document.querySelector(
    "#portfolio-value-status",
);

if (refreshButton && portfolioValue && portfolioValueStatus) {
    const usdFormatter = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
    });

    refreshButton.addEventListener("click", async () => {
        refreshButton.disabled = true;
        portfolioValueStatus.textContent = "Updating portfolio value...";

        try {
            const response = await fetch(refreshButton.dataset.valueUrl, {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Unable to update portfolio value.");
            }

            portfolioValue.textContent = usdFormatter.format(data.total);
            portfolioValueStatus.textContent = "Updated just now.";
        } catch (error) {
            portfolioValueStatus.textContent =
                error instanceof Error
                    ? error.message
                    : "Unable to update portfolio value.";
        } finally {
            refreshButton.disabled = false;
        }
    });
}
