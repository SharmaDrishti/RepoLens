import { useEffect, useId, useMemo, useRef, useState } from "react";
import { category, edgeDrawing, importLayout, nodeHeight, nodeWidth } from "./import-layout";
import type { ImportEdge } from "./import-layout";
import "./explorer.css";

const name = (path: string) => path.split("/").at(-1) ?? path;

export function ImportExplorer({ paths, edges, activeEdges, selected, selectedEdge, select, inspect }: {
  paths: string[]; edges: ImportEdge[]; activeEdges: string[]; selected?: string; selectedEdge?: string;
  select: (path: string) => void; inspect: (edge: ImportEdge) => void;
}) {
  const [zoom, setZoom] = useState<number | "fit">("fit");
  const [bounds, setBounds] = useState({width: 620, height: 420});
  const [filter, setFilter] = useState("");
  const [group, setGroup] = useState("");
  const viewport = useRef<HTMLDivElement>(null);
  const drag = useRef<{x: number; y: number; left: number; top: number} | null>(null);
  const arrow = useId();
  const {items, matching, visibleEdges, drawing} = useMemo(() => {
    const matches = paths.filter(path => (!group || category(path) === group) &&
      path.toLowerCase().includes(filter.toLowerCase().trim()));
    const items = matches.slice(0, 60);
    if (matches.length > 60 && selected && matches.includes(selected) && !items.includes(selected)) items[59] = selected;
    const included = new Set(items);
    const visibleEdges = edges.filter(edge => included.has(edge.from) && included.has(edge.to));
    return {items, matching: matches.length, visibleEdges, drawing: importLayout(items, visibleEdges)};
  }, [paths, edges, filter, group, selected]);
  const fit = Math.min(1, Math.max(.45, Math.min(bounds.width / drawing.width, bounds.height / drawing.height)));
  const scale = zoom === "fit" ? fit : zoom;
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const measure = () => setBounds({width: element.clientWidth, height: 420});
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  function focus() {
    const point = selected ? drawing.points.get(selected) : undefined;
    const element = viewport.current;
    if (!point || !element) return;
    element.scrollTo({left: (point.x + nodeWidth / 2) * scale - element.clientWidth / 2,
      top: (point.y + nodeHeight / 2) * scale - element.clientHeight / 2,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"});
  }
  function reset() {
    setFilter(""); setGroup(""); setZoom("fit"); viewport.current?.scrollTo(0, 0);
  }
  const groups = [...new Set(paths.map(category))].sort();
  return <div className="import-explorer">
    <div className="explorer-toolbar">
      <label>Find a file <input type="search" value={filter} onChange={event => setFilter(event.target.value)} /></label>
      <label>File category <select value={group} onChange={event => setGroup(event.target.value)}>
        <option value="">All categories</option>{groups.map(item => <option key={item}>{item}</option>)}
      </select></label>
      <div className="explorer-controls" role="group" aria-label="Map view controls">
        <button type="button" aria-label="Zoom out" onClick={() => setZoom(Math.max(.45, scale - .15))}>−</button>
        <button type="button" aria-label="Zoom in" onClick={() => setZoom(Math.min(2, scale + .15))}>+</button>
        <button type="button" onClick={() => { setZoom("fit"); viewport.current?.scrollTo(0, 0); }}>Fit</button>
        <button type="button" onClick={reset}>Reset view</button>
        <button type="button" disabled={!selected || !drawing.points.has(selected)} onClick={focus}>Focus file</button>
      </div>
    </div>
    <p className="explorer-summary">{items.length} of {matching} matching files · {visibleEdges.length} imports · {Math.round(scale * 100)}%
      {matching > 60 && " · Narrow the category or search to see more files."}</p>
    <div className="explorer-viewport" ref={viewport} tabIndex={0} aria-label="Scrollable import map"
      onPointerDown={event => {
        if (event.pointerType !== "mouse" || event.button !== 0 || (event.target as Element).closest("button,[role=button]")) return;
        const box = event.currentTarget;
        drag.current = {x: event.clientX, y: event.clientY, left: box.scrollLeft, top: box.scrollTop};
        box.setPointerCapture(event.pointerId);
      }}
      onPointerMove={event => {
        if (!drag.current) return;
        const {x, y, left, top} = drag.current;
        event.currentTarget.scrollTo(left + x - event.clientX, top + y - event.clientY);
      }}
      onLostPointerCapture={() => {drag.current = null;}}
      onKeyDown={event => {
        if (event.target !== event.currentTarget) return;
        const offsets: Record<string, [number, number]> = {
          ArrowLeft: [-55, 0], ArrowRight: [55, 0], ArrowUp: [0, -55], ArrowDown: [0, 55],
        };
        const offset = offsets[event.key];
        if (offset) {event.preventDefault(); event.currentTarget.scrollBy(...offset);}
      }}>
      {!items.length ? <p className="explorer-summary">No files match these filters.</p> :
        <div style={{width: drawing.width * scale, height: drawing.height * scale, marginInline: "auto", position: "relative", overflow: "clip"}}>
          <div className="explorer-canvas" style={{width: drawing.width, height: drawing.height, transform: `scale(${scale})`}}>
            <svg width={drawing.width} height={drawing.height} aria-label="Measured import directions">
              <defs><marker id={arrow} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M0 0L10 5 0 10z" fill="#6e436c" /></marker></defs>
              {visibleEdges.map(edge => {
                const d = edgeDrawing(drawing.points.get(edge.from)!, drawing.points.get(edge.to)!);
                const lit = activeEdges.includes(edge.id) || selectedEdge === edge.id ||
                  selected === edge.from || selected === edge.to;
                return <g key={edge.id} data-edge={edge.id} data-from={edge.from} data-to={edge.to}>
                  <path d={d} markerEnd={`url(#${arrow})`} aria-hidden="true" className={lit ? "explorer-edge emphasized" : selected || selectedEdge ? "explorer-edge muted-edge" : "explorer-edge"} />
                  <path d={d} className="explorer-hit" role="button" tabIndex={0}
                    aria-label={`Inspect import from ${edge.from} to ${edge.to}`} aria-pressed={selectedEdge === edge.id}
                    onClick={() => inspect(edge)} onKeyDown={event => {
                      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); inspect(edge); }
                    }} />
                </g>;
              })}
            </svg>
            {[...drawing.points].map(([path, point]) => <button key={path} type="button"
              data-category={category(path)} className="explorer-node" aria-pressed={selected === path} data-search-match={!!filter.trim()} title={path}
              aria-label={`Inspect file ${path}`} onClick={() => select(path)}
              style={{left: point.x, top: point.y, width: nodeWidth, minHeight: nodeHeight}}>
              <small>{category(path)}</small><strong>{name(path)}</strong>
            </button>)}
          </div>
        </div>}
    </div>
    <p className="explorer-summary">Drag the background, swipe, or focus the map and use the arrow keys to pan.</p>
  </div>;
}
