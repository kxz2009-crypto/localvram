/** Cost comparison for the same workload, in the user's chosen currency.
 * Defaults belong to the UI and are examples, not current market quotes.
 */
export function calculateCosts(input) {
  const required = ['months','hours','activeWatts','idleWatts','electricity','localMaintenance','purchase','resale','cloudRate','cloudTimeRatio','cloudExtras'];
  for (const key of required) {
    if (typeof input[key] !== 'number' || !Number.isFinite(input[key]) || input[key] < 0) throw new Error('invalid_number');
  }
  if (!['owned','purchase'].includes(input.mode)) throw new Error('invalid_mode');
  if (!Number.isInteger(input.months) || input.months < 1 || input.months > 120 || input.hours > 730 || input.cloudTimeRatio <= 0) throw new Error('invalid_range');
  if (input.mode === 'purchase' && input.resale > input.purchase) throw new Error('resale_above_purchase');
  const upfront = input.mode === 'purchase' ? input.purchase : 0;
  const residual = input.mode === 'purchase' ? input.resale : 0;
  const localElectricity = (input.hours * input.activeWatts + (730-input.hours) * input.idleWatts) / 1000 * input.electricity;
  const localMonthly = localElectricity + input.localMaintenance;
  const cloudHours = input.hours * input.cloudTimeRatio;
  const cloudMonthly = cloudHours * input.cloudRate + input.cloudExtras;
  const monthlySavings = cloudMonthly - localMonthly;
  // Cash payback excludes a speculative resale before the horizon ends.
  const paybackMonths = input.mode === 'purchase' && monthlySavings > 0 ? upfront / monthlySavings : null;
  const localTotal = upfront + input.months * localMonthly - residual;
  const cloudTotal = input.months * cloudMonthly;
  const result = { upfront, residual, localElectricity, localMonthly, cloudHours, cloudMonthly, localTotal, cloudTotal,
    savings:cloudTotal-localTotal, paybackMonths,
    paybackWithinHorizon:paybackMonths !== null && paybackMonths <= input.months };
  if (Object.values(result).some(value => typeof value === 'number' && !Number.isFinite(value))) throw new Error('invalid_range');
  return result;
}

/** Generation-only workload estimate using user-measured speeds, never guessed model benchmarks. */
export function workloadFromTokens(millionTokens, localTokensPerSecond, cloudTokensPerSecond) {
  if (![millionTokens,localTokensPerSecond,cloudTokensPerSecond].every(value => typeof value === 'number' && Number.isFinite(value)) || millionTokens < 0 || localTokensPerSecond <= 0 || cloudTokensPerSecond <= 0) throw new Error('invalid_throughput');
  const hours = millionTokens * 1e6 / localTokensPerSecond / 3600;
  const cloudTimeRatio = localTokensPerSecond / cloudTokensPerSecond;
  if (!Number.isFinite(hours) || hours > 730 || !Number.isFinite(cloudTimeRatio) || cloudTimeRatio <= 0) throw new Error('invalid_workload');
  return { hours, cloudTimeRatio };
}
