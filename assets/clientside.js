window.dash_clientside = Object.assign({}, window.dash_clientside, {
    bcr: {
        playPause: function (caClicks, vnClicks, currentView, activeTab, selectedAct, compareMode, animMode, caText, vnText) {
            const tr = window.dash_clientside.callback_context.triggered;
            if (!tr || !tr.length) return [caText || "▶ Play", "primary", vnText || "▶ Play", "primary"];

            const prop_id = tr[0].prop_id;
            const triggeredId = prop_id.split('.')[0];

            const gdCa = document.querySelector('#chart-ca .js-plotly-plot');
            const gdVn = document.querySelector('#chart-vn .js-plotly-plot');

            function stopRaf(gd, snapToCurrent) {
                if (!gd) return;
                if (gd.__bcrRafId) {
                    window.cancelAnimationFrame(gd.__bcrRafId);
                    gd.__bcrRafId = null;
                }
                if (gd.__bcrState) {
                    gd.__bcrState.playing = false;
                    if (snapToCurrent) {
                        const idx = Math.round(gd.__bcrState.cursor || 0);
                        applyDiscreteFrame(gd, idx);
                    }
                }
            }

            // Reset buttons & stop animations when view, tab, selected category, or compare mode changes
            if (['current-view', 'view-tabs', 'selected-activity', 'compare-mode'].includes(triggeredId)) {
                stopRaf(gdCa, false);
                stopRaf(gdVn, false);
                return ["▶ Play", "primary", "▶ Play", "primary"];
            }

            const isParallel = (animMode === 'parallel');
            const STEP_DURATION_SEC = 0.30; // 300ms per 15-min step (~28s for 24h), smooth 60fps Flourish-style glide

                    function ensureFramesSnapshot(gd) {
                        if (!gd || !gd._transitionData || !gd._transitionData._frames || !gd._transitionData._frames.length) {
                            return gd && gd.__bcrSavedFrames ? gd.__bcrSavedFrames : [];
                        }
                            const rawFrames = gd._transitionData._frames;
                            if (!gd.__bcrSavedFrames || gd.__bcrRawRef !== rawFrames[0]) {
                                gd.__bcrRawRef = rawFrames[0];
                                gd.__bcrSavedFrames = rawFrames.map(f => ({
                                    name: f.name,
                                    data: (f.data || []).map(tr => ({
                                        x: tr.x ? tr.x.slice() : [],
                                        y: tr.y ? tr.y.slice() : [],
                                        text: tr.text ? tr.text.slice() : [],
                                        yaxis: tr.yaxis || 'y'
                                    }))
                                }));
                                gd.__bcrState = null;
                            }
                            return gd.__bcrSavedFrames;
                        }

                                    function bindSliderListener(gd) {
                                        if (!gd || gd.__bcrSliderListenerBound || typeof gd.on !== 'function') return;
                                        gd.__bcrSliderListenerBound = true;
                                        gd.on('plotly_sliderchange', function (evt) {
                                            const frames = ensureFramesSnapshot(gd);
                                            if (!frames.length) return;
                                            let idx = 0;
                                            if (evt && evt.slider && typeof evt.slider.active === 'number') {
                                                idx = evt.slider.active;
                                            } else if (evt && evt.step && evt.step.label) {
                                                const found = frames.findIndex(f => f.name === evt.step.label);
                                                if (found !== -1) idx = found;
                                            }
                                                if (!gd.__bcrState) {
                                                    gd.__bcrState = { playing: false, cursor: idx, visualY: null };
                                                } else {
                                                    gd.__bcrState.cursor = idx;
                                                    gd.__bcrState.visualY = null;
                                                }
                                                if (!gd.__bcrState.playing) {
                                                    applyDiscreteFrame(gd, idx);
                                                }
                                            });
                                    }

                                    function getActiveSliderIdx(gd, totalFrames) {
                                        let idx = 0;
                                            if (gd && gd.__bcrState && typeof gd.__bcrState.cursor === 'number') {
                                                idx = Math.round(gd.__bcrState.cursor);
                                            } else if (gd && gd._fullLayout && gd._fullLayout.sliders && gd._fullLayout.sliders[0] && typeof gd._fullLayout.sliders[0].active === 'number') {
                                                idx = gd._fullLayout.sliders[0].active;
                                            } else if (gd && gd.layout && gd.layout.sliders && gd.layout.sliders[0] && typeof gd.layout.sliders[0].active === 'number') {
                                                idx = gd.layout.sliders[0].active;
                                            }
                                            if (totalFrames > 0 && idx >= totalFrames - 1) {
                                                idx = 0;
                                            }
                                            return Math.max(0, idx);
                                        }

                                            function getPanelGroups(gd) {
                                                const groups = {};
                                                if (!gd || !gd.data) return [];
                                                gd.data.forEach((tr, idx) => {
                                                    const yRef = tr.yaxis || 'y';
                                                    if (!groups[yRef]) groups[yRef] = [];
                                                    groups[yRef].push(idx);
                                                });
                                                return Object.keys(groups).map(yRef => ({
                                                    yRef: yRef,
                                                    layoutKey: yRef === 'y' ? 'yaxis' : 'yaxis' + yRef.slice(1),
                                                    traceIndices: groups[yRef]
                                                }));
                                            }

                                            function applyDiscreteFrame(gd, frameIdx) {
                                                const frames = ensureFramesSnapshot(gd);
                                                if (!gd || !window.Plotly || !frames.length) return;
                                                const clampedIdx = Math.min(Math.max(0, frameIdx), frames.length - 1);
                                                const frame = frames[clampedIdx];
                                                const panelGroups = getPanelGroups(gd);

                                                panelGroups.forEach(pg => {
                                                    const mainIdx = pg.traceIndices[0];
                                                    if (frame.data[mainIdx]) {
                                                        const yArr = frame.data[mainIdx].y.slice();
                                                        if (gd.layout && gd.layout[pg.layoutKey]) {
                                                            gd.layout[pg.layoutKey].tickvals = yArr;
                                                        }
                                                    }
                                                    pg.traceIndices.forEach(tIdx => {
                                                        if (frame.data[tIdx] && gd.data[tIdx]) {
                                                            gd.data[tIdx].x = frame.data[tIdx].x.slice();
                                                            gd.data[tIdx].y = frame.data[tIdx].y.slice();
                                                            gd.data[tIdx].text = frame.data[tIdx].text.slice();
                                                        }
                                                    });
                                                });

                                                if (gd.layout && gd.layout.sliders && gd.layout.sliders[0]) {
                                                    gd.layout.sliders[0].active = clampedIdx;
                                                }
                                                if (gd._fullLayout && gd._fullLayout.sliders && gd._fullLayout.sliders[0]) {
                                                    gd._fullLayout.sliders[0].active = clampedIdx;
                                                    gd._fullLayout.sliders[0]._dragging = false;
                                                }
                                                if (!gd.__bcrState) {
                                                    gd.__bcrState = { playing: false, cursor: clampedIdx, visualY: null };
                                                } else {
                                                    gd.__bcrState.cursor = clampedIdx;
                                                    gd.__bcrState.visualY = panelGroups.map(pg => frame.data[pg.traceIndices[0]].y.slice());
                                                }
                                                window.Plotly.react(gd, gd.data, gd.layout);
                                            }

                                            function formatBarTexts(pg, f0Data, interpMainX, interpOvX) {
                                                const mainIdx = pg.traceIndices[0];
                                                const ovIdx = pg.traceIndices.length > 1 ? pg.traceIndices[1] : null;
                                                const refTexts = f0Data[mainIdx].text || [];
                                                const nCats = interpMainX.length;
                                                const mainTexts = new Array(nCats);
                                                const ovTexts = ovIdx !== null ? new Array(nCats) : null;

                                                for (let k = 0; k < nCats; k++) {
                                                    const v = interpMainX[k];
                                                    const sample = refTexts[k] || "";
                                                    if (ovIdx !== null && interpOvX && interpOvX[k] !== null && interpOvX[k] !== undefined) {
                                                        const ovVal = interpOvX[k];
                                                        const ovSample = (f0Data[ovIdx].text && f0Data[ovIdx].text[k]) || sample;
                                                        const match = (sample + " " + ovSample).match(/\(([A-Z]+):/);
                                                        const otherShort = match ? match[1] : "Other";
                                                        const compLabel = " <b>" + v.toFixed(1) + "%</b> (" + otherShort + ": " + ovVal.toFixed(1) + "%)";
                                                        if (v >= ovVal) {
                                                            mainTexts[k] = compLabel;
                                                            ovTexts[k] = "";
                                                        } else {
                                                            mainTexts[k] = "";
                                                            ovTexts[k] = compLabel;
                                                        }
                                                    } else if (sample.indexOf("<b>") !== -1) {
                                                        mainTexts[k] = " <b>" + v.toFixed(1) + "%</b>";
                                                        if (ovTexts) ovTexts[k] = "";
                                                    } else {
                                                        mainTexts[k] = " " + v.toFixed(1) + "%";
                                                        if (ovTexts) ovTexts[k] = "";
                                                    }
                                                }
                                                return { mainTexts: mainTexts, ovTexts: ovTexts };
                                            }

                                            function startFlourishAnimation(gd, startIdx, btnId) {
                                                const frames = ensureFramesSnapshot(gd);
                                                if (!gd || !window.Plotly || !frames.length) return;
                                                bindSliderListener(gd);
                                                stopRaf(gd, false);

                                                const totalFrames = frames.length;
                                                const panelGroups = getPanelGroups(gd);
                                                const initFrame = frames[startIdx];

                                                gd.__bcrState = {
                                                    playing: true,
                                                    cursor: startIdx,
                                                    lastTs: null,
                                                    visualY: panelGroups.map(pg => initFrame.data[pg.traceIndices[0]].y.slice())
                                                };

                                                function step(ts) {
                                                    if (!gd.__bcrState || !gd.__bcrState.playing) return;
                                                    if (gd.__bcrState.lastTs === null) {
                                                        gd.__bcrState.lastTs = ts;
                                                    }
                                                    const dt = Math.min(0.05, Math.max(0.001, (ts - gd.__bcrState.lastTs) / 1000));
                                                    gd.__bcrState.lastTs = ts;

                                                    gd.__bcrState.cursor = Math.min(totalFrames - 1, gd.__bcrState.cursor + dt / STEP_DURATION_SEC);
                                                    const cursor = gd.__bcrState.cursor;
                                                    const m = Math.floor(cursor);
                                                    const nextM = Math.min(m + 1, totalFrames - 1);
                                                    const alpha = cursor - m;

                                                    const f0 = frames[m];
                                                    const f1 = frames[nextM];
                                                    const smoothFactor = 1 - Math.exp(-12.0 * dt);
                                                    let maxRankDiff = 0;

                                                    panelGroups.forEach((pg, pIdx) => {
                                                        const mainIdx = pg.traceIndices[0];
                                                        const ovIdx = pg.traceIndices.length > 1 ? pg.traceIndices[1] : null;
                                                        const x0 = f0.data[mainIdx].x;
                                                        const x1 = f1.data[mainIdx].x;
                                                        const nCats = x0.length;

                                                        const interpMainX = new Array(nCats);
                                                        for (let k = 0; k < nCats; k++) {
                                                            interpMainX[k] = x0[k] + alpha * (x1[k] - x0[k]);
                                                        }

                                                        let interpOvX = null;
                                                        if (ovIdx !== null) {
                                                            const ox0 = f0.data[ovIdx].x;
                                                            const ox1 = f1.data[ovIdx].x;
                                                            interpOvX = new Array(nCats);
                                                            for (let k = 0; k < nCats; k++) {
                                                                if (ox0[k] === null || ox0[k] === undefined || ox1[k] === null || ox1[k] === undefined) {
                                                                    interpOvX[k] = ox1[k];
                                                                } else {
                                                                    interpOvX[k] = ox0[k] + alpha * (ox1[k] - ox0[k]);
                                                                }
                                                            }
                                                        }

                                                        // Compute instantaneous target rank from current interpolated bar lengths
                                                        const order = Array.from({ length: nCats }, (_, i) => i).sort((a, b) => {
                                                            const va = Math.round(interpMainX[a] * 10000);
                                                            const vb = Math.round(interpMainX[b] * 10000);
                                                            if (va !== vb) return va - vb;
                                                            return b - a;
                                                        });
                                                        const targetY = new Array(nCats);
                                                        for (let r = 0; r < nCats; r++) {
                                                            targetY[order[r]] = r;
                                                        }

                                                        // Flourish-style smooth vertical rank interpolation on Y-axis
                                                        const visY = gd.__bcrState.visualY[pIdx];
                                                        const plotY = new Array(nCats);
                                                        for (let k = 0; k < nCats; k++) {
                                                            const diff = targetY[k] - visY[k];
                                                            if (Math.abs(diff) < 0.002) {
                                                                visY[k] = targetY[k];
                                                            } else {
                                                                visY[k] += diff * smoothFactor;
                                                                const rem = Math.abs(targetY[k] - visY[k]);
                                                                if (rem > maxRankDiff) maxRankDiff = rem;
                                                            }
                                                            plotY[k] = visY[k] + k * 1e-5;
                                                        }

                                                        const texts = formatBarTexts(pg, f0.data, interpMainX, interpOvX);
                                                        gd.data[mainIdx].x = interpMainX;
                                                        gd.data[mainIdx].y = plotY;
                                                        gd.data[mainIdx].text = texts.mainTexts;

                                                        if (ovIdx !== null && interpOvX) {
                                                            gd.data[ovIdx].x = interpOvX;
                                                            gd.data[ovIdx].y = plotY.slice();
                                                            gd.data[ovIdx].text = texts.ovTexts;
                                                        }

                                                        if (gd.layout && gd.layout[pg.layoutKey]) {
                                                            gd.layout[pg.layoutKey].tickvals = plotY;
                                                        }
                                                    });

                                                    const sliderIdx = Math.round(cursor);
                                                    if (gd.layout && gd.layout.sliders && gd.layout.sliders[0]) {
                                                        gd.layout.sliders[0].active = sliderIdx;
                                                    }
                                                    if (gd._fullLayout && gd._fullLayout.sliders && gd._fullLayout.sliders[0]) {
                                                        gd._fullLayout.sliders[0].active = sliderIdx;
                                                        gd._fullLayout.sliders[0]._dragging = false;
                                                    }

                                                    window.Plotly.react(gd, gd.data, gd.layout);

                                                    if (cursor >= totalFrames - 1 && maxRankDiff <= 0.005) {
                                                        gd.__bcrState.playing = false;
                                                        gd.__bcrRafId = null;
                                                        if (window.dash_clientside && window.dash_clientside.set_props && btnId) {
                                                            window.dash_clientside.set_props(btnId, { children: "▶ Play", color: "primary" });
                                                        }
                                                        return;
                                                    }

                                                    gd.__bcrRafId = window.requestAnimationFrame(step);
                                                }

                                                gd.__bcrRafId = window.requestAnimationFrame(step);
                                            }

                                            if (triggeredId === 'btn-play-ca') {
                                                const isPlaying = (caText === '⏸ Pause');
                                                if (isPlaying) {
                                                        stopRaf(gdCa, true);
                                                        if (isParallel && gdVn) {
                                                            stopRaf(gdVn, true);
                                                            return ["▶ Play", "primary", "▶ Play", "primary"];
                                                        }
                                                        return ["▶ Play", "primary", vnText, vnText === '⏸ Pause' ? "secondary" : "primary"];
                                                    } else {
                                                            const framesCa = ensureFramesSnapshot(gdCa);
                                                            const startIdx = getActiveSliderIdx(gdCa, framesCa.length);
                                                            startFlourishAnimation(gdCa, startIdx, 'btn-play-ca');
                                                            if (isParallel && gdVn) {
                                                                ensureFramesSnapshot(gdVn);
                                                                startFlourishAnimation(gdVn, startIdx, 'btn-play-vn');
                                                                return ["⏸ Pause", "secondary", "⏸ Pause", "secondary"];
                                                            }
                                                            return ["⏸ Pause", "secondary", vnText, vnText === '⏸ Pause' ? "secondary" : "primary"];
                                                        }
                                                    } else if (triggeredId === 'btn-play-vn') {
                                                        const isPlaying = (vnText === '⏸ Pause');
                                                        if (isPlaying) {
                                                                stopRaf(gdVn, true);
                                                                if (isParallel && gdCa) {
                                                                    stopRaf(gdCa, true);
                                                                    return ["▶ Play", "primary", "▶ Play", "primary"];
                                                                }
                                                                return [caText, caText === '⏸ Pause' ? "secondary" : "primary", "▶ Play", "primary"];
                                                            } else {
                                                                    const framesVn = ensureFramesSnapshot(gdVn);
                                                                    const startIdx = getActiveSliderIdx(gdVn, framesVn.length);
                                                                    startFlourishAnimation(gdVn, startIdx, 'btn-play-vn');
                                                                    if (isParallel && gdCa) {
                                                                        ensureFramesSnapshot(gdCa);
                                                                        startFlourishAnimation(gdCa, startIdx, 'btn-play-ca');
                                                                        return ["⏸ Pause", "secondary", "⏸ Pause", "secondary"];
                                                                    }
                                                                    return [caText, caText === '⏸ Pause' ? "secondary" : "primary", "⏸ Pause", "secondary"];
                                                                }
                                                            }
                                                            return [caText, "primary", vnText, "primary"];
                                                        }
                                                    }
                                            });

                            // Synchronize each column filter box outer width to match its exact DataTable column width
                            (function () {
                                function syncCountryFilterWidths(country) {
                                    const container = document.getElementById('table-container-' + country);
                                    if (!container || container.style.display === 'none') return;
                                    const filterBar = document.getElementById('table-filters-' + country);
                                    if (!filterBar) return;
                                    const ths = container.querySelectorAll('th.dash-header');
                                    if (!ths || !ths.length) return;
                                    const visibleItems = Array.from(filterBar.querySelectorAll('.table-filter-item')).filter(
                                        el => el.style.display !== 'none' && window.getComputedStyle(el).display !== 'none'
                                    );
                                    if (visibleItems.length !== ths.length) return;
                                    for (let i = 0; i < ths.length; i++) {
                                        const w = ths[i].getBoundingClientRect().width;
                                        if (w > 0) {
                                            const px = w.toFixed(2) + 'px';
                                            if (visibleItems[i].style.width !== px) {
                                                visibleItems[i].style.width = px;
                                                visibleItems[i].style.flex = '0 0 ' + px;
                                                visibleItems[i].style.maxWidth = px;
                                            }
                                        }
                                    }
                                }

                                function syncAllFilterWidths() {
                                    syncCountryFilterWidths('ca');
                                    syncCountryFilterWidths('vn');
                                }

                                window.addEventListener('resize', function () {
                                    window.requestAnimationFrame(syncAllFilterWidths);
                                });

                                const obs = new MutationObserver(function () {
                                    window.requestAnimationFrame(syncAllFilterWidths);
                                });

                                function initObserver() {
                                    if (document.body) {
                                        obs.observe(document.body, {
                                            childList: true,
                                            subtree: true,
                                            attributes: true,
                                            attributeFilter: ['style', 'class']
                                        });
                                        syncAllFilterWidths();
                                    } else {
                                        window.addEventListener('DOMContentLoaded', initObserver);
                                    }
                                }
                                initObserver();
                            })();
