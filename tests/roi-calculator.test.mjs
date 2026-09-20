import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateCosts } from '../src/lib/roi-calculator.js';
const base={mode:'purchase',months:24,hours:120,activeWatts:350,idleWatts:40,electricity:0.15,localMaintenance:5,purchase:1500,resale:300,cloudRate:1,cloudTimeRatio:1,cloudExtras:8};
const close=(actual,expected)=>assert.ok(Math.abs(actual-expected)<1e-8,`${actual} != ${expected}`);
test('total costs include power, maintenance and end-of-horizon resale exactly once',()=>{
 const r=calculateCosts(base);close(r.localElectricity,9.96);close(r.localTotal,1559.04);close(r.cloudTotal,3072);close(r.savings,1512.96);
 close(r.paybackMonths,1500/(128-14.96));assert.equal(r.paybackWithinHorizon,true);
});
test('owned hardware excludes historical purchase and resale',()=>{
 const r=calculateCosts({...base,mode:'owned'});close(r.localTotal,359.04);assert.equal(r.residual,0);assert.equal(r.paybackMonths,null);
});
test('zero usage still includes idle power, but switching off removes it',()=>{
 close(calculateCosts({...base,hours:0}).localElectricity,4.38);
 close(calculateCosts({...base,hours:0,idleWatts:0}).localElectricity,0);
});
test('equivalent workload accounts for different cloud throughput',()=>{
 const r=calculateCosts({...base,cloudTimeRatio:0.5});close(r.cloudHours,60);close(r.cloudMonthly,68);
 assert.equal(r.paybackWithinHorizon,false);
});
test('cloud cheaper gives no operating-savings payback',()=>{
 const r=calculateCosts({...base,cloudRate:0,cloudExtras:0});assert.equal(r.paybackMonths,null);assert.ok(r.savings<0);
});
test('invalid, nonfinite and impossible inputs are rejected',()=>{
 for(const input of [{hours:731},{months:1.5},{months:0},{cloudTimeRatio:0},{resale:1501},{electricity:-1},{cloudRate:NaN},{activeWatts:Infinity},{mode:'other'}]) assert.throws(()=>calculateCosts({...base,...input}));
});

test('model workload converts measured token speeds into equivalent runtime', async()=>{
 const {workloadFromTokens}=await import('../src/lib/roi-calculator.js');
 const w=workloadFromTokens(3.6,10,20);
 close(w.hours,100);close(w.cloudTimeRatio,0.5);
 const result=calculateCosts({...base,...w});close(result.cloudHours,50);
 const slower=calculateCosts({...base,...workloadFromTokens(3.6,5,20)});
 close(slower.cloudHours,50);assert.ok(slower.localElectricity>result.localElectricity);
});
test('missing speeds and workloads beyond monthly local capacity fail closed', async()=>{
 const {workloadFromTokens}=await import('../src/lib/roi-calculator.js');
 for(const args of [[10,0,20],[10,10,NaN],[-1,10,20],[100,1,20],[Infinity,10,20]]) assert.throws(()=>workloadFromTokens(...args));
 assert.equal(workloadFromTokens(0,10,20).hours,0);
});
