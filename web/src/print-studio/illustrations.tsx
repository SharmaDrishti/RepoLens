import type { Workshop } from "./simulation";
import { along, height, origin, placements, route, stations, stationStates, width } from "./track";
import type { Point } from "./track";

const inks = ["#ef9b89", "#f8d873", "#cfb8ee", "#a0ceb8", "#a9c6e4"];
const plum = "#492f46";

function Ticket({ id, point, state }: { id: number; point: Point; state?: string }) {
  return <g data-ticket={id} data-state={state} transform={`translate(${point.x} ${point.y})`}>
    <path d="M-25-14h47l5 5v24h-52z" fill="#6e5260" opacity=".24" transform="translate(1 3)" />
    <path d="M-25-14h47l5 5v24h-52z" fill={inks[(id - 1) % inks.length]} stroke={plum} strokeWidth="1.6" />
    <path d="M17-13v27" stroke={plum} strokeDasharray="2 2" opacity=".65" />
    <path d="M-17 5h19m-19 4h12" stroke={plum} strokeWidth="1.2" strokeLinecap="round" />
    <text x="-17" y="1" className="studio-ticket-number">{String(id).padStart(2, "0")}</text>
  </g>;
}

function Press({ point, variant, fraction, available }: { point: Point; variant: number; fraction?: number; available: boolean }) {
  const active = fraction !== undefined;
  return <g transform={`translate(${point.x} ${point.y})`}>
    <ellipse cx="2" cy="43" rx="71" ry="9" fill="#654353" opacity=".13" />
    <path d="M-69-41l13-12H61l10 12v85H-69z" fill={available ? "#c9c5db" : "#d9cbd2"} stroke={plum} strokeWidth="1.7" />
    <path d="M-69-41h140v77H-69z" fill={available ? ["#b6a5ce", "#9abfae", "#d4a197", "#a3b8d2"][variant] : "#cebbc7"} stroke={plum} strokeWidth="1.7" />
    <path d="M-66 25H67v12l-9 7H-58l-8-7z" fill="#715970" stroke={plum} strokeWidth="1.7" />
    <path d="M-58-36h38a9 9 0 0 1 9 9v44h-47zM51-36h13v53H51z" fill="#f5e8ef" opacity=".65" />
    <path d="M-31-23h69a6 6 0 0 1 6 6v35h-81v-35a6 6 0 0 1 6-6z" fill="#533b52" />
    <path d="M-31 17h68M-31-20h67" stroke="#e6cadc" strokeWidth="3" />
    <path d="M-59 27h111" stroke="#d8c4e2" strokeWidth="3" strokeLinecap="round" />
    {active && <path d={`M-59 27h${111 * fraction}`} stroke="#f8d873" strokeWidth="3" strokeLinecap="round" />}
    <circle cx="-52" cy="-24" r="4" fill={active ? "#a0ceb8" : "#eee0d7"} stroke={plum} />
    <circle cx="55" cy="-24" r={variant % 2 ? 8 : 5} fill="#f4d6a9" stroke={plum} />
    {variant % 2 === 0 && <path d="M-58-47H57m-100 3H43" stroke="#f7dbc2" strokeWidth="2" />}
    <path d="M50-10h10m-10 5h10" stroke={plum} strokeWidth="1.3" strokeLinecap="round" />
  </g>;
}

function Tray({ x, y, fill }: { x: number; y: number; fill: string }) {
  return <g transform={`translate(${x} ${y})`}>
    <path d="M-5 154h150l-10 11H6z" fill="#977184" opacity=".27" />
    <path d="M8-31h125l10 12v173H-5V-19z" fill={fill} stroke={plum} strokeWidth="1.7" />
    <path d="M5-16h128v166H5zM5 30h128M5 72h128M5 114h128M69-16v166" fill="none" stroke="#805a6e" strokeOpacity=".55" />
  </g>;
}

export function ProductionLine({ workshop, previous, motion = 1, arrival = false, title }: {
  workshop: Workshop; previous?: Workshop; motion?: number; arrival?: boolean; title: string;
}) {
  const tickets = placements(workshop);
  const states = stationStates(workshop);
  const prior = new Map(previous ? placements(previous).map(ticket => [ticket.id, ticket]) : []);
  const progress = (fraction: number) => fraction * fraction * (3 - 2 * fraction);
  const paper = (ticket: typeof tickets[number]) => {
    const old = prior.get(ticket.id);
    if (arrival && ticket.id === 1) return along([origin, {x: 215, y: 145}, {x: 225, y: 193},
      {x: ticket.point.x, y: 193}, ticket.point], progress(motion));
    if (!old || motion === 1 || old.state === ticket.state) return ticket.point;
    const adjusted = ticket.state === "running" ? Math.max(0, (motion - .18) / .82) : motion;
    return along(route(old, ticket, old.point), progress(adjusted));
  };
  return <svg className="production-line" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
    <rect x="5" y="6" width="810" height="395" rx="32" fill="#f8ebdc" />
    <path d="M6 227h808v140q0 33-33 33H40Q6 400 6 366z" fill="#eddbce" />
    <path d="M6 315h808m-727 0-32 84m141-84-14 84m515-84 29 84" fill="none" stroke="#c6acb6" strokeWidth="1.2" />
    <path d="M270 53a65 46 0 0 1 130 0v78H270zm150 0a80 46 0 0 1 160 0v78H420z"
      fill="#efe0ed" stroke="#c8a8c2" strokeWidth="1.5" />
    <path d="M6 218h808" stroke="#c8ac9a" strokeWidth="1.5" />
    <path d="M206 185h409v18H206z" fill="#ccb09d" stroke="#855f70" />
    <path d="M217 189h387m-387 9h387" stroke="#f4e4c6" strokeWidth="2" />
    <path d="M346 103v179m164-179v179M188 194h447" fill="none" stroke="#9d7a84" strokeWidth="2" strokeDasharray="4 7" />
    <path d="M57 77h134l15 13v34H53V90z" fill="#deb581" stroke={plum} strokeWidth="1.8" />
    <path d="M53 90h153M60 116h135M65 97h103" fill="none" stroke={plum} strokeWidth="1.3" />
    <path d="M60 47h100l15 16v25H60z" fill="#f8d873" stroke={plum} strokeWidth="1.6" />
    <path d="M70 57h77m-77 9h62m-62 9h35" stroke="#714e61" strokeWidth="2" strokeLinecap="round" />
    <Tray x={47} y={163} fill="#f2dbc6" />
    <Tray x={638} y={163} fill="#d3e7d8" />
    <path d="M622 56h131v49H622z" fill="#c9ddef" stroke="#876c8a" strokeWidth="1.5" />
    <path d="M632 66h112m-112 9h94m-94 9h56" stroke="#876c8a" strokeWidth="1.8" strokeLinecap="round" />
    {stations.map((point, slot) => {
      const job = tickets.find(item => item.slot === slot);
      return states[slot] === "closed"
        ? <g key={slot} data-station="closed" transform={`translate(${point.x} ${point.y})`}>
          <rect x="-67" y="-43" width="134" height="82" rx="8" fill="#eadfe1" stroke="#896e80" strokeDasharray="5 5" />
          <text textAnchor="middle" y="5" className="studio-art-label">Closed</text>
        </g>
        : <g key={slot} data-station={states[slot]}><Press point={point} variant={slot} fraction={job?.progress} available />
          {states[slot] === "open" && <text x={point.x} y={point.y + 4} textAnchor="middle" className="studio-open-label">Open</text>}
        </g>;
    })}
    {tickets.map(ticket => <Ticket key={ticket.id} id={ticket.id} state={ticket.state} point={paper(ticket)} />)}
    <path d="M237 344h338l-20 17H254z" fill="#655069" stroke={plum} strokeWidth="1.7" />
    <path d="M255 361h300v20H255z" fill="#aa8192" stroke={plum} strokeWidth="1.7" />
    <path d="M275 369h115m41 0h103" stroke="#e4c4c2" strokeWidth="2" />
  </svg>;
}

export function EditorialHero({ animate }: { animate: boolean }) {
  return <svg viewBox="0 0 650 450" role="img" aria-label="Two working presses with a stack of colorful jobs waiting to print">
    <path d="M178 337V130a142 111 0 0 1 284 0v207z" fill="#e9d8ef" stroke="#a982a0" strokeWidth="2" />
    <path d="M195 317V131a125 95 0 0 1 250 0v186z" fill="#d4e5ef" stroke="#a982a0" strokeWidth="2" />
    <path d="M320 39v280M195 138h250m-250 62h250" stroke="#a982a0" strokeWidth="2" />
    <path d="M476 22v80m-49 35q6-41 49-41t49 41z" fill="#e59584" stroke={plum} strokeWidth="2.5" />
    <ellipse cx="476" cy="137" rx="49" ry="8" fill="#f8db8c" stroke={plum} strokeWidth="2" />
    <path d="M42 355q94-19 213-17h275q78 4 89 25-44 29-213 34H250Q77 394 42 355z" fill="#d4abb0" opacity=".42" />
    <path d="M100 298h435l45 32H50z" fill="#f4d6a9" stroke={plum} strokeWidth="2.5" />
    <path d="M50 330h530v18H50zm28 18h23v36H78zm453 0h23v36h-23z" fill="#ae7f87" stroke={plum} strokeWidth="2.5" />
    <path d="M107 335h420" stroke="#eec4aa" strokeWidth="2" />
    <g>
      <path d="M65 246l82-7 32 36-95 13z" fill="#9fcbb7" stroke={plum} strokeWidth="2" />
      <path d="M64 237l85-8 29 33-92 16z" fill="#f2d474" stroke={plum} strokeWidth="2" />
      <path d="M64 228l83-7 22 30-86 12z" fill="#ef9b89" stroke={plum} strokeWidth="2" />
      <path d="m84 239 55-7m-49 16 44-6" stroke={plum} strokeWidth="2" strokeLinecap="round" />
    </g>
    <Press point={{x: 284, y: 243}} variant={0} fraction={.6} available />
    <Press point={{x: 455, y: 243}} variant={1} fraction={.33} available />
    <g className={animate ? "hero-ticket" : undefined}><Ticket id={1} point={{x: 284, y: 243}} /></g>
    <Ticket id={2} point={{x: 455, y: 243}} />
    <path d="M351 301h69l17 16h-87z" fill="#f8db8c" stroke={plum} strokeWidth="1.8" />
    <path d="M362 306h52m-51 5h33" stroke={plum} strokeWidth="1.5" />
  </svg>;
}
