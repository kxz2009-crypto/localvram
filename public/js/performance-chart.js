(function () {
  function isNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function formatValue(value) {
    if (!isNumber(value)) {
      return "";
    }
    if (Math.abs(value) >= 100) {
      return String(Math.round(value));
    }
    return value.toFixed(1).replace(/\.0$/, "");
  }

  function niceMax(value) {
    if (!isNumber(value) || value <= 0) {
      return 1;
    }
    var exponent = Math.floor(Math.log10(value));
    var step = Math.pow(10, exponent);
    var normalized = value / step;
    var nice = normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
    return nice * step;
  }

  function cssVar(name, fallback) {
    var styles = window.getComputedStyle(document.documentElement);
    return styles.getPropertyValue(name).trim() || fallback;
  }

  function renderLineChart(canvas, config) {
    if (!canvas || !canvas.getContext) {
      return function () {};
    }

    var ctx = canvas.getContext("2d");
    var labels = Array.isArray(config.labels) ? config.labels : [];
    var datasets = (Array.isArray(config.datasets) ? config.datasets : []).filter(function (dataset) {
      return dataset && Array.isArray(dataset.data);
    });
    var yAxisLabel = config.yAxisLabel || "";
    var rightAxisLabel = config.rightAxisLabel || "";
    var destroyed = false;
    var observer = null;

    function draw() {
      if (destroyed) {
        return;
      }

      var parent = canvas.parentElement;
      var rect = canvas.getBoundingClientRect();
      var width = Math.max(320, Math.floor(rect.width || (parent ? parent.clientWidth : 640) || 640));
      var height = Math.max(220, Math.floor(rect.height || 280));
      var dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      canvas.dataset.chartRendered = "true";

      var textColor = cssVar("--muted", "#64748b");
      var strongColor = cssVar("--text", "#0f172a");
      var gridColor = "rgba(148, 163, 184, 0.22)";
      var axisColor = "rgba(100, 116, 139, 0.55)";
      var chartLeft = 58;
      var chartRight = rightAxisLabel ? 58 : 22;
      var chartTop = 34;
      var chartBottom = 54;
      var plotWidth = width - chartLeft - chartRight;
      var plotHeight = height - chartTop - chartBottom;

      if (!labels.length || !datasets.length || plotWidth <= 0 || plotHeight <= 0) {
        ctx.fillStyle = textColor;
        ctx.font = "13px system-ui, sans-serif";
        ctx.fillText("No chart data available", chartLeft, chartTop + 24);
        return;
      }

      var leftValues = [];
      var rightValues = [];
      datasets.forEach(function (dataset) {
        var bucket = dataset.axis === "right" ? rightValues : leftValues;
        dataset.data.forEach(function (value) {
          if (isNumber(value)) {
            bucket.push(value);
          }
        });
      });
      if (!leftValues.length && rightValues.length) {
        leftValues = rightValues.slice();
      }

      var leftMax = niceMax(Math.max.apply(null, leftValues.concat([1])) * 1.12);
      var rightMax = rightValues.length ? niceMax(Math.max.apply(null, rightValues.concat([1])) * 1.12) : leftMax;

      function xAt(index) {
        if (labels.length === 1) {
          return chartLeft + plotWidth / 2;
        }
        return chartLeft + (plotWidth * index) / (labels.length - 1);
      }

      function yAt(value, axis) {
        var max = axis === "right" ? rightMax : leftMax;
        return chartTop + plotHeight - (Math.max(0, value) / max) * plotHeight;
      }

      ctx.lineWidth = 1;
      ctx.strokeStyle = gridColor;
      ctx.fillStyle = textColor;
      ctx.font = "12px system-ui, sans-serif";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";

      for (var tick = 0; tick <= 4; tick += 1) {
        var y = chartTop + plotHeight - (plotHeight * tick) / 4;
        var leftValue = (leftMax * tick) / 4;
        ctx.beginPath();
        ctx.moveTo(chartLeft, y);
        ctx.lineTo(chartLeft + plotWidth, y);
        ctx.stroke();
        ctx.fillText(formatValue(leftValue), chartLeft - 8, y);

        if (rightAxisLabel && rightValues.length) {
          ctx.textAlign = "left";
          ctx.fillText(formatValue((rightMax * tick) / 4), chartLeft + plotWidth + 8, y);
          ctx.textAlign = "right";
        }
      }

      ctx.strokeStyle = axisColor;
      ctx.beginPath();
      ctx.moveTo(chartLeft, chartTop);
      ctx.lineTo(chartLeft, chartTop + plotHeight);
      ctx.lineTo(chartLeft + plotWidth, chartTop + plotHeight);
      ctx.stroke();

      if (rightAxisLabel) {
        ctx.beginPath();
        ctx.moveTo(chartLeft + plotWidth, chartTop);
        ctx.lineTo(chartLeft + plotWidth, chartTop + plotHeight);
        ctx.stroke();
      }

      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      labels.forEach(function (label, index) {
        var x = xAt(index);
        var shortLabel = String(label).length > 24 ? String(label).slice(0, 22) + "..." : String(label);
        ctx.fillStyle = textColor;
        ctx.fillText(shortLabel, x, chartTop + plotHeight + 14);
      });

      ctx.save();
      ctx.translate(16, chartTop + plotHeight / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillStyle = textColor;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(yAxisLabel, 0, 0);
      ctx.restore();

      if (rightAxisLabel) {
        ctx.save();
        ctx.translate(width - 14, chartTop + plotHeight / 2);
        ctx.rotate(Math.PI / 2);
        ctx.fillStyle = textColor;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(rightAxisLabel, 0, 0);
        ctx.restore();
      }

      var legendX = chartLeft;
      datasets.forEach(function (dataset) {
        var color = dataset.borderColor || "#2563eb";
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(legendX, 16);
        ctx.lineTo(legendX + 22, 16);
        ctx.stroke();
        ctx.fillStyle = strongColor;
        ctx.font = "12px system-ui, sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        var label = String(dataset.label || "");
        ctx.fillText(label, legendX + 28, 16);
        legendX += Math.min(230, 42 + ctx.measureText(label).width);
      });

      datasets.forEach(function (dataset) {
        var color = dataset.borderColor || "#2563eb";
        var values = dataset.data;
        var axis = dataset.axis === "right" ? "right" : "left";
        ctx.strokeStyle = color;
        ctx.lineWidth = dataset.borderWidth || 2;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";

        var started = false;
        ctx.beginPath();
        values.forEach(function (value, index) {
          if (!isNumber(value)) {
            return;
          }
          var x = xAt(index);
          var y = yAt(value, axis);
          if (!started) {
            ctx.moveTo(x, y);
            started = true;
          } else {
            ctx.lineTo(x, y);
          }
        });
        if (started) {
          ctx.stroke();
        }

        values.forEach(function (value, index) {
          if (!isNumber(value)) {
            return;
          }
          var x = xAt(index);
          var y = yAt(value, axis);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(x, y, dataset.pointRadius || 4, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = strongColor;
          ctx.font = "11px system-ui, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "bottom";
          ctx.fillText(formatValue(value), x, y - 7);
        });
      });
    }

    draw();
    if ("ResizeObserver" in window) {
      observer = new ResizeObserver(draw);
      observer.observe(canvas.parentElement || canvas);
    } else {
      window.addEventListener("resize", draw);
    }

    return function destroy() {
      destroyed = true;
      if (observer) {
        observer.disconnect();
      } else {
        window.removeEventListener("resize", draw);
      }
    };
  }

  window.LocalVRAMCharts = Object.assign(window.LocalVRAMCharts || {}, {
    renderLineChart: renderLineChart,
  });
  window.dispatchEvent(new Event("localvram:charts-ready"));
})();
