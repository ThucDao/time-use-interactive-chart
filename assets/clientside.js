window.dash_clientside = Object.assign({}, window.dash_clientside, {
    bcr: {
        playPause: function (caClicks, vnClicks, currentView, activeTab, selectedAct, compareMode, animMode, caText, vnText) {
            const tr = window.dash_clientside.callback_context.triggered;
            if (!tr || !tr.length) return [caText || "▶ Play", "primary", vnText || "▶ Play", "primary"];

            const prop_id = tr[0].prop_id;
            const triggeredId = prop_id.split('.')[0];

            // Reset buttons when view, tab, selected category, or compare mode changes (since figure is recreated)
            if (['current-view', 'view-tabs', 'selected-activity', 'compare-mode'].includes(triggeredId)) {
                return ["▶ Play", "primary", "▶ Play", "primary"];
            }

            const gdCa = document.querySelector('#chart-ca .js-plotly-plot');
            const gdVn = document.querySelector('#chart-vn .js-plotly-plot');
            const isParallel = (animMode === 'parallel');

            const animOptions = {
                frame: { duration: 180, redraw: true },
                fromcurrent: false,
                mode: 'immediate',
                transition: { duration: 50, easing: 'linear' }
            };
            const pauseOptions = { mode: 'immediate', frame: { duration: 0, redraw: false }, transition: { duration: 0 } };

            function getFrameNames(gd) {
                if (gd && gd._transitionData && gd._transitionData._frames && gd._transitionData._frames.length) {
                    return gd._transitionData._frames.map(f => f.name);
                }
                if (gd && gd.layout && gd.layout.sliders && gd.layout.sliders[0] && gd.layout.sliders[0].steps) {
                    return gd.layout.sliders[0].steps.map(s => s.label);
                }
                return [];
            }

            function ensureSliderSyncOnAnimate(gd) {
                if (!gd || gd.__bcrSliderSyncBound || typeof gd.on !== 'function') return;
                gd.__bcrSliderSyncBound = true;
                gd.on('plotly_animatingframe', function (evt) {
                    if (!evt || !evt.name) return;
                    const names = getFrameNames(gd);
                    const idx = names.indexOf(evt.name);
                    if (idx === -1) return;
                    if (gd.layout && gd.layout.sliders && gd.layout.sliders[0]) {
                        gd.layout.sliders[0].active = idx;
                    }
                    if (gd._fullLayout && gd._fullLayout.sliders && gd._fullLayout.sliders[0]) {
                        gd._fullLayout.sliders[0].active = idx;
                        gd._fullLayout.sliders[0]._dragging = false;
                        gd._fullLayout._currentFrame = evt.name;
                    }
                });
            }

            function getActiveSliderIdx(gd, totalFrames) {
                let idx = 0;
                if (gd && gd._fullLayout && gd._fullLayout.sliders && gd._fullLayout.sliders[0] && typeof gd._fullLayout.sliders[0].active === 'number') {
                    idx = gd._fullLayout.sliders[0].active;
                } else if (gd && gd.layout && gd.layout.sliders && gd.layout.sliders[0] && typeof gd.layout.sliders[0].active === 'number') {
                    idx = gd.layout.sliders[0].active;
                }
                if (totalFrames > 0 && idx >= totalFrames - 1) {
                    idx = 0;
                }
                return idx;
            }

            function startAnimationFromIdx(gd, frameNames, startIdx) {
                if (!gd || !window.Plotly || !frameNames.length) return;
                ensureSliderSyncOnAnimate(gd);
                const remainingFrames = frameNames.slice(startIdx);
                if (!remainingFrames.length) return;
                if (gd.layout && gd.layout.sliders && gd.layout.sliders[0]) {
                    gd.layout.sliders[0].active = startIdx;
                }
                if (gd._fullLayout && gd._fullLayout.sliders && gd._fullLayout.sliders[0]) {
                    gd._fullLayout.sliders[0].active = startIdx;
                    gd._fullLayout.sliders[0]._dragging = false;
                }
                window.Plotly.animate(gd, remainingFrames, animOptions);
            }

            if (triggeredId === 'btn-play-ca') {
                const isPlaying = (caText === '⏸ Pause');
                if (isPlaying) {
                    if (gdCa && window.Plotly) window.Plotly.animate(gdCa, [null], pauseOptions);
                    if (isParallel && gdVn && window.Plotly) {
                        window.Plotly.animate(gdVn, [null], pauseOptions);
                        return ["▶ Play", "primary", "▶ Play", "primary"];
                    }
                    return ["▶ Play", "primary", vnText, vnText === '⏸ Pause' ? "secondary" : "primary"];
                } else {
                    const frameNames = getFrameNames(gdCa);
                    const startIdx = getActiveSliderIdx(gdCa, frameNames.length);
                    startAnimationFromIdx(gdCa, frameNames, startIdx);
                    if (isParallel && gdVn && window.Plotly) {
                        startAnimationFromIdx(gdVn, frameNames, startIdx);
                        return ["⏸ Pause", "secondary", "⏸ Pause", "secondary"];
                    }
                    return ["⏸ Pause", "secondary", vnText, vnText === '⏸ Pause' ? "secondary" : "primary"];
                }
            } else if (triggeredId === 'btn-play-vn') {
                const isPlaying = (vnText === '⏸ Pause');
                if (isPlaying) {
                    if (gdVn && window.Plotly) window.Plotly.animate(gdVn, [null], pauseOptions);
                    if (isParallel && gdCa && window.Plotly) {
                        window.Plotly.animate(gdCa, [null], pauseOptions);
                        return ["▶ Play", "primary", "▶ Play", "primary"];
                    }
                    return [caText, caText === '⏸ Pause' ? "secondary" : "primary", "▶ Play", "primary"];
                } else {
                    const frameNames = getFrameNames(gdVn);
                    const startIdx = getActiveSliderIdx(gdVn, frameNames.length);
                    startAnimationFromIdx(gdVn, frameNames, startIdx);
                    if (isParallel && gdCa && window.Plotly) {
                        startAnimationFromIdx(gdCa, frameNames, startIdx);
                        return ["⏸ Pause", "secondary", "⏸ Pause", "secondary"];
                    }
                    return [caText, caText === '⏸ Pause' ? "secondary" : "primary", "⏸ Pause", "secondary"];
                }
            }
            return [caText, "primary", vnText, "primary"];
        }
    }
});
