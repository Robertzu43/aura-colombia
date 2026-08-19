import { DurableObject } from 'cloudflare:workers';

const K = 32, AURA_BASE = 1000;
const NOMBRES = new Set([
  "Shakira",
  "Karol G",
  "J Balvin",
  "Maluma",
  "Feid",
  "Juanes",
  "Carlos Vives",
  "Camilo",
  "Sebastián Yatra",
  "Manuel Turizo",
  "Ryan Castro",
  "Blessd",
  "Kali Uchis",
  "Fonseca",
  "Andrés Cepeda",
  "Fanny Lu",
  "Greeicy",
  "Mike Bahía",
  "Silvestre Dangond",
  "Jorge Celedón",
  "Jessi Uribe",
  "Paola Jara",
  "Pipe Bueno",
  "Yeison Jiménez",
  "Andy Rivera",
  "Goyo",
  "Totó la Momposina",
  "Diomedes Díaz",
  "Joe Arroyo",
  "Farina",
  "Kris R",
  "James Rodríguez",
  "Luis Díaz",
  "Radamel Falcao",
  "Juan G. Cuadrado",
  "David Ospina",
  "Yerry Mina",
  "Dayro Moreno",
  "Carlos Valderrama",
  "René Higuita",
  "Faustino Asprilla",
  "Iván R. Córdoba",
  "Mario Yepes",
  "Linda Caicedo",
  "Catalina Usme",
  "Gustavo Puerta",
  "Egan Bernal",
  "Nairo Quintana",
  "Rigoberto Urán",
  "Fernando Gaviria",
  "Esteban Chaves",
  "Lucho Herrera",
  "Mariana Pajón",
  "Caterine Ibargüen",
  "María Isabel Urrutia",
  "Óscar Figueroa",
  "Juan Pablo Montoya",
  "Camilo Villegas",
  "Édgar Rentería",
  "Kid Pambelé",
  "Happy Lora",
  "Robert Farah",
  "Sofía Vergara",
  "John Leguizamo",
  "Catalina Sandino",
  "Manolo Cardona",
  "Juan Pablo Raba",
  "Carmen Villalobos",
  "Andrés Parra",
  "Danna García",
  "Margarita Rosa de Francisco",
  "Amparo Grisales",
  "Carolina Cruz",
  "Laura Acuña",
  "Claudia Bahamón",
  "Esperanza Gómez",
  "Alejandro Riaño",
  "Suso el Paspi",
  "Andrés López",
  "Hassam",
  "Iván Marín",
  "Vicky Dávila",
  "Juan Gossaín",
  "Luisa Fernanda W",
  "Yeferson Cossio",
  "Westcol",
  "La Liendra",
  "Aida Victoria Merlano",
  "Epa Colombia",
  "Kika Nieto",
  "Pautips",
  "Dani Duke",
  "La Segura",
  "Cris Valencia",
  "Gabriel García Márquez",
  "Fernando Botero",
  "Rodolfo Llinás",
  "Diana Trujillo",
  "David Vélez",
  "Simón Borrero",
  "Freddy Vega",
  "Gustavo Petro",
  "Álvaro Uribe",
  "Juan Manuel Santos",
  "Francia Márquez",
  "Paulina Vega"
]);

export class AuraGlobal extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec('CREATE TABLE IF NOT EXISTS aura (nombre TEXT PRIMARY KEY, puntos INTEGER)');
    this.sql.exec("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v INTEGER)");
    this.sql.exec("INSERT OR IGNORE INTO meta VALUES ('votos', 0)");
  }
  ranking() {
    const aura = {};
    for (const r of this.sql.exec('SELECT nombre, puntos FROM aura')) aura[r.nombre] = r.puntos;
    return { aura, votos: this.sql.exec("SELECT v FROM meta WHERE k='votos'").one().v };
  }
  votar(ganador, perdedor) {
    const get = n => {
      const filas = this.sql.exec('SELECT puntos FROM aura WHERE nombre = ?', n).toArray();
      return filas.length ? filas[0].puntos : AURA_BASE;
    };
    const ra = get(ganador), rb = get(perdedor);
    const delta = Math.max(1, Math.round(K * (1 - 1 / (1 + Math.pow(10, (rb - ra) / 400)))));
    this.sql.exec('INSERT INTO aura VALUES (?, ?) ON CONFLICT(nombre) DO UPDATE SET puntos = excluded.puntos', ganador, ra + delta);
    this.sql.exec('INSERT INTO aura VALUES (?, ?) ON CONFLICT(nombre) DO UPDATE SET puntos = excluded.puntos', perdedor, rb - delta);
    this.sql.exec("UPDATE meta SET v = v + 1 WHERE k='votos'");
    return { delta, ganador: ra + delta, perdedor: rb - delta, votos: this.sql.exec("SELECT v FROM meta WHERE k='votos'").one().v };
  }
}

// ponytail: anti-spam en memoria por isolate (se pierde al reciclar, no cubre botnets);
// si el abuso se vuelve real, pasar al binding de Rate Limiting de Cloudflare
const golpes = new Map();
function spam(ip) {
  const ahora = Date.now();
  const g = golpes.get(ip);
  if (!g || ahora - g.desde > 10_000) { golpes.set(ip, { desde: ahora, n: 1 }); return false; }
  return ++g.n > 15;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const stub = env.AURA.get(env.AURA.idFromName('lanzamiento')); // instancia fresca: el estado de pruebas quedó en 'global'
    if (url.pathname === '/api/ranking') return Response.json(await stub.ranking());
    if (url.pathname === '/api/votar' && req.method === 'POST') {
      if (spam(req.headers.get('cf-connecting-ip') || '?')) return new Response('calma, pana', { status: 429 });
      const { ganador, perdedor } = await req.json().catch(() => ({}));
      if (!NOMBRES.has(ganador) || !NOMBRES.has(perdedor) || ganador === perdedor)
        return new Response('nombre invalido', { status: 400 });
      return Response.json(await stub.votar(ganador, perdedor));
    }
    return new Response('Not found', { status: 404 });
  }
};
