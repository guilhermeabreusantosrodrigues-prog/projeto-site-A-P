import { useEffect, useState } from "react";

/*
  URL da API Python.
  Em um projeto real, isso pode ficar em uma variável de ambiente (.env).
*/
const API = "http://127.0.0.1:8000";

const categorias = [
  "Eletrônico",
  "Material escolar",
  "Roupa",
  "Acessório",
  "Documento",
  "Chave",
  "Outro",
];

const initialLost = {
  nome_usuario: "",
  email_usuario: "",
  nome_objeto: "",
  categoria: "",
  marca: "",
  modelo: "",
  cor: "",
  data_perda: "",
  local_perda: "",
  descricao: "",
};

const initialFound = {
  nome_objeto: "",
  categoria: "",
  marca: "",
  modelo: "",
  cor: "",
  data_encontrado: "",
  local_encontrado: "",
  descricao: "",
};

function Field({ label, children, wide = false }) {
  return (
    <label className={wide ? "field wide" : "field"}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function App() {
  const [lost, setLost] = useState(initialLost);
  const [found, setFound] = useState(initialFound);

  const [perdidos, setPerdidos] = useState([]);
  const [encontrados, setEncontrados] = useState([]);
  const [matches, setMatches] = useState([]);

  const [message, setMessage] = useState("");

  async function carregarDados() {
    const [p, e] = await Promise.all([
      fetch(`${API}/api/objetos-perdidos`),
      fetch(`${API}/api/objetos-encontrados`),
    ]);

    setPerdidos(await p.json());
    setEncontrados(await e.json());
  }

  useEffect(() => {
    carregarDados();
  }, []);

  function updateLost(event) {
    const { name, value } = event.target;
    setLost((old) => ({ ...old, [name]: value }));
  }

  function updateFound(event) {
    const { name, value } = event.target;
    setFound((old) => ({ ...old, [name]: value }));
  }

  async function enviarPerdido(event) {
    event.preventDefault();
    setMessage("Enviando...");

    const response = await fetch(`${API}/api/objetos-perdidos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lost),
    });

    if (!response.ok) {
      setMessage("Não foi possível cadastrar o objeto.");
      return;
    }

    setMessage("Objeto perdido registrado com sucesso.");
    setLost(initialLost);
    carregarDados();
  }

  async function enviarEncontrado(event) {
    event.preventDefault();
    setMessage("Cadastrando objeto encontrado...");

    const response = await fetch(`${API}/api/objetos-encontrados`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(found),
    });

    if (!response.ok) {
      setMessage("Não foi possível cadastrar o objeto.");
      return;
    }

    setMessage("Objeto encontrado cadastrado.");
    setFound(initialFound);
    carregarDados();
  }

  async function procurarMatches() {
    const response = await fetch(`${API}/api/matches`);
    setMatches(await response.json());
  }

  return (
    <div>
      <header className="header">
        <div className="logo">
          <div className="logoBox">A&P</div>
          <div>
            <strong>Achados & Perdidos</strong>
            <small>SENAC</small>
          </div>
        </div>

        <nav>
          <a href="#inicio">Início</a>
          <a href="#perdi">Perdi</a>
          <a href="#encontrados">Encontrados</a>
          <a href="#senac">Área SENAC</a>
        </nav>
      </header>

      <main>
        <section id="inicio" className="hero">
          <div>
            <p className="tag">SISTEMA DIGITAL • PROTÓTIPO</p>
            <h1>
              Seu objeto pode estar
              <em> mais perto do que você imagina.</em>
            </h1>
            <p className="heroText">
              Registre uma perda, consulte objetos encontrados e deixe o
              sistema procurar possíveis correspondências.
            </p>

            <div className="actions">
              <a className="button primary" href="#perdi">
                Registrar objeto perdido
              </a>
              <a className="button ghost" href="#encontrados">
                Ver encontrados
              </a>
            </div>
          </div>

          <div className="dashboardCard">
            <div className="online">
              <i /> SISTEMA ONLINE
            </div>

            <h3>Central A&P</h3>
            <p>Monitoramento dos registros e possíveis correspondências.</p>

            <div className="numbers">
              <div>
                <b>{perdidos.length}</b>
                <span>Perdidos</span>
              </div>
              <div>
                <b>{encontrados.length}</b>
                <span>Encontrados</span>
              </div>
            </div>
          </div>
        </section>

        <section id="perdi" className="section">
          <div className="sectionTitle">
            <p className="tag">PARA ALUNOS E FUNCIONÁRIOS</p>
            <h2>Perdi um objeto</h2>
            <p>
              Informe o máximo de características possível. Essas informações
              serão usadas pelo mecanismo de comparação.
            </p>
          </div>

          <form className="panel" onSubmit={enviarPerdido}>
            <div className="grid">
              <Field label="Seu nome *">
                <input name="nome_usuario" value={lost.nome_usuario}
                  onChange={updateLost} required />
              </Field>

              <Field label="E-mail *">
                <input type="email" name="email_usuario"
                  value={lost.email_usuario} onChange={updateLost} required />
              </Field>

              <Field label="Nome do objeto *">
                <input name="nome_objeto" value={lost.nome_objeto}
                  onChange={updateLost} required placeholder="Ex.: Mochila" />
              </Field>

              <Field label="Categoria *">
                <select name="categoria" value={lost.categoria}
                  onChange={updateLost} required>
                  <option value="">Selecione</option>
                  {categorias.map((c) => <option key={c}>{c}</option>)}
                </select>
              </Field>

              <Field label="Marca">
                <input name="marca" value={lost.marca} onChange={updateLost} />
              </Field>

              <Field label="Modelo">
                <input name="modelo" value={lost.modelo} onChange={updateLost} />
              </Field>

              <Field label="Cor">
                <input name="cor" value={lost.cor} onChange={updateLost} />
              </Field>

              <Field label="Data aproximada">
                <input type="date" name="data_perda"
                  value={lost.data_perda} onChange={updateLost} />
              </Field>

              <Field label="Onde perdeu?" wide>
                <input name="local_perda" value={lost.local_perda}
                  onChange={updateLost}
                  placeholder="Ex.: Prédio G / sala G308" />
              </Field>

              <Field label="Descrição detalhada *" wide>
                <textarea name="descricao" value={lost.descricao}
                  onChange={updateLost} required
                  placeholder="Características, adesivos, detalhes, marcas de uso..." />
              </Field>
            </div>

            <div className="formBottom">
              <span>* Campos obrigatórios</span>
              <button className="button primary">Enviar ocorrência</button>
            </div>
          </form>
        </section>

        <section id="encontrados" className="section darkSection">
          <div className="sectionTitle">
            <p className="tag">CONSULTA</p>
            <h2>Objetos encontrados</h2>
            <p>
              Protótipo de consulta pública. No sistema final, informações
              sensíveis não devem ser expostas.
            </p>
          </div>

          <div className="cards">
            {encontrados.length === 0 && (
              <div className="empty">Nenhum objeto encontrado cadastrado.</div>
            )}

            {encontrados.map((item) => (
              <article className="objectCard" key={item.id}>
                <span className="pill">{item.categoria}</span>
                <h3>{item.nome_objeto}</h3>
                <p>{item.cor || "Cor não informada"} • {item.marca || "Marca não informada"}</p>
                <small>{item.local_encontrado || "Local não informado"}</small>
              </article>
            ))}
          </div>
        </section>

        <section id="senac" className="section">
          <div className="sectionTitle">
            <p className="tag">ÁREA INTERNA</p>
            <h2>Cadastro de objeto encontrado</h2>
            <p>
              Tela demonstrativa para o funcionário responsável pelo A&P.
            </p>
          </div>

          <form className="panel" onSubmit={enviarEncontrado}>
            <div className="grid">
              <Field label="Nome do objeto *">
                <input name="nome_objeto" value={found.nome_objeto}
                  onChange={updateFound} required />
              </Field>

              <Field label="Categoria *">
                <select name="categoria" value={found.categoria}
                  onChange={updateFound} required>
                  <option value="">Selecione</option>
                  {categorias.map((c) => <option key={c}>{c}</option>)}
                </select>
              </Field>

              <Field label="Marca">
                <input name="marca" value={found.marca} onChange={updateFound} />
              </Field>

              <Field label="Modelo">
                <input name="modelo" value={found.modelo} onChange={updateFound} />
              </Field>

              <Field label="Cor">
                <input name="cor" value={found.cor} onChange={updateFound} />
              </Field>

              <Field label="Data encontrada">
                <input type="date" name="data_encontrado"
                  value={found.data_encontrado} onChange={updateFound} />
              </Field>

              <Field label="Local encontrado" wide>
                <input name="local_encontrado"
                  value={found.local_encontrado}
                  onChange={updateFound}
                  placeholder="Ex.: Biblioteca" />
              </Field>

              <Field label="Descrição *" wide>
                <textarea name="descricao" value={found.descricao}
                  onChange={updateFound} required />
              </Field>
            </div>

            <div className="formBottom">
              <span>Uso interno do SENAC</span>
              <button className="button primary">Cadastrar encontrado</button>
            </div>
          </form>

          <div className="matching">
            <div className="matchHeader">
              <div>
                <p className="tag">MATCHING</p>
                <h2>Possíveis correspondências</h2>
              </div>

              <button className="button ghost" onClick={procurarMatches}>
                Procurar matches
              </button>
            </div>

            <div className="cards">
              {matches.length === 0 && (
                <div className="empty">
                  Nenhuma correspondência calculada ainda.
                </div>
              )}

              {matches.map((m, index) => (
                <article className="matchCard" key={index}>
                  <div className="score">{m.score}%</div>
                  <h3>{m.perdido} ↔ {m.encontrado}</h3>
                  <p>Possível proprietário: <b>{m.usuario}</b></p>
                  <small>{m.motivos.join(" • ")}</small>
                </article>
              ))}
            </div>
          </div>

          {message && <div className="toast">{message}</div>}
        </section>
      </main>

      <footer>
        <strong>A&P SENAC</strong>
        <span>Protótipo acadêmico • React + FastAPI</span>
      </footer>
    </div>
  );
}

export default App;