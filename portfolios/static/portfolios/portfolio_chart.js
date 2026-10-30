"use strict";

const chartCanvas = document.querySelector("#portfolio-value-chart");
const historyElement = document.querySelector("#portfolio-value-history");

if (chartCanvas && historyElement) {
    const points = JSON.parse(historyElement.textContent).map((point) => ({
        date: new Date(`${point.date}T00:00:00Z`),
        value: Number(point.value),
    }));
    const context = chartCanvas.getContext("2d");
    const currencyFormatter = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
    });
    const dateFormatter = new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
    });
    const tooltipCurrencyFormatter = new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    let chartCoordinates = [];
    let hoveredIndex = null;

    function drawPortfolioChart() {
        const bounds = chartCanvas.getBoundingClientRect();
        if (!context || bounds.width === 0 || bounds.height === 0) {
            return;
        }

        const pixelRatio = window.devicePixelRatio || 1;
        chartCanvas.width = Math.round(bounds.width * pixelRatio);
        chartCanvas.height = Math.round(bounds.height * pixelRatio);
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

        const width = bounds.width;
        const height = bounds.height;
        const padding = { top: 16, right: 16, bottom: 36, left: 76 };
        const plotWidth = width - padding.left - padding.right;
        const plotHeight = height - padding.top - padding.bottom;
        const values = points.map((point) => point.value);
        let minimum = Math.min(...values);
        let maximum = Math.max(...values);

        if (minimum === maximum) {
            const paddingValue = minimum === 0 ? 1 : Math.abs(minimum) * 0.05;
            minimum = Math.max(0, minimum - paddingValue);
            maximum += paddingValue;
        }

        context.clearRect(0, 0, width, height);
        context.font = "12px system-ui, sans-serif";
        context.textBaseline = "middle";

        for (let tick = 0; tick <= 4; tick += 1) {
            const fraction = tick / 4;
            const y = padding.top + fraction * plotHeight;
            const value = maximum - fraction * (maximum - minimum);

            context.strokeStyle = "#dee2e6";
            context.beginPath();
            context.moveTo(padding.left, y);
            context.lineTo(width - padding.right, y);
            context.stroke();

            context.fillStyle = "#6c757d";
            context.textAlign = "right";
            context.fillText(
                currencyFormatter.format(value),
                padding.left - 8,
                y,
            );
        }

        chartCoordinates = points.map((point, index) => ({
            x:
                padding.left +
                (points.length === 1
                    ? plotWidth / 2
                    : (index / (points.length - 1)) * plotWidth),
            y:
                padding.top +
                ((maximum - point.value) / (maximum - minimum)) * plotHeight,
        }));

        if (chartCoordinates.length > 0) {
            const fill = context.createLinearGradient(
                0,
                padding.top,
                0,
                padding.top + plotHeight,
            );
            fill.addColorStop(0, "rgba(13, 110, 253, 0.2)");
            fill.addColorStop(1, "rgba(13, 110, 253, 0)");
            context.beginPath();
            context.moveTo(chartCoordinates[0].x, padding.top + plotHeight);
            chartCoordinates.forEach((point) => context.lineTo(point.x, point.y));
            context.lineTo(
                chartCoordinates[chartCoordinates.length - 1].x,
                padding.top + plotHeight,
            );
            context.closePath();
            context.fillStyle = fill;
            context.fill();

            context.beginPath();
            chartCoordinates.forEach((point, index) => {
                if (index === 0) {
                    context.moveTo(point.x, point.y);
                } else {
                    context.lineTo(point.x, point.y);
                }
            });
            context.strokeStyle = "#0d6efd";
            context.lineWidth = 2;
            context.stroke();

            if (chartCoordinates.length === 1) {
                context.beginPath();
                context.arc(
                    chartCoordinates[0].x,
                    chartCoordinates[0].y,
                    4,
                    0,
                    2 * Math.PI,
                );
                context.fillStyle = "#0d6efd";
                context.fill();
            }

            if (hoveredIndex !== null) {
                const point = chartCoordinates[hoveredIndex];
                context.beginPath();
                context.arc(point.x, point.y, 5, 0, 2 * Math.PI);
                context.fillStyle = "#0d6efd";
                context.fill();
                context.strokeStyle = "#ffffff";
                context.lineWidth = 2;
                context.stroke();

                const dateLabel = dateFormatter.format(points[hoveredIndex].date);
                const valueLabel = tooltipCurrencyFormatter.format(
                    points[hoveredIndex].value,
                );
                context.font = "12px system-ui, sans-serif";
                const tooltipWidth =
                    Math.max(
                        context.measureText(dateLabel).width,
                        context.measureText(valueLabel).width,
                    ) + 20;
                const tooltipHeight = 44;
                let tooltipX = point.x + 12;
                let tooltipY = point.y - tooltipHeight - 12;

                if (tooltipX + tooltipWidth > width - padding.right) {
                    tooltipX = point.x - tooltipWidth - 12;
                }
                if (tooltipY < padding.top) {
                    tooltipY = point.y + 12;
                }
                tooltipX = Math.max(
                    padding.left,
                    Math.min(tooltipX, width - padding.right - tooltipWidth),
                );
                tooltipY = Math.max(
                    padding.top,
                    Math.min(tooltipY, height - padding.bottom - tooltipHeight),
                );

                context.fillStyle = "#212529";
                context.fillRect(tooltipX, tooltipY, tooltipWidth, tooltipHeight);
                context.fillStyle = "#ced4da";
                context.textAlign = "left";
                context.fillText(dateLabel, tooltipX + 10, tooltipY + 13);
                context.fillStyle = "#ffffff";
                context.font = "600 12px system-ui, sans-serif";
                context.fillText(valueLabel, tooltipX + 10, tooltipY + 32);
            }
        }

        const labelIndices =
            points.length === 1 ? [0] : [0, points.length - 1];
        labelIndices.forEach((index) => {
            const point = points[index];
            const x =
                padding.left +
                (points.length === 1
                    ? plotWidth / 2
                    : (index / (points.length - 1)) * plotWidth);
            context.fillStyle = "#6c757d";
            context.textAlign = index === 0 ? "left" : "right";
            context.fillText(
                dateFormatter.format(point.date),
                x,
                height - padding.bottom / 2,
            );
        });
    }

    drawPortfolioChart();
    window.addEventListener("resize", drawPortfolioChart);
    chartCanvas.addEventListener("pointermove", (event) => {
        const bounds = chartCanvas.getBoundingClientRect();
        const pointerX = event.clientX - bounds.left;
        const pointerY = event.clientY - bounds.top;
        let nearestIndex = null;
        let nearestDistance = 12;

        chartCoordinates.forEach((point, index) => {
            const distance = Math.hypot(point.x - pointerX, point.y - pointerY);
            if (distance < nearestDistance) {
                nearestDistance = distance;
                nearestIndex = index;
            }
        });

        if (nearestIndex !== hoveredIndex) {
            hoveredIndex = nearestIndex;
            drawPortfolioChart();
        }
    });
    chartCanvas.addEventListener("pointerleave", () => {
        if (hoveredIndex !== null) {
            hoveredIndex = null;
            drawPortfolioChart();
        }
    });
}
