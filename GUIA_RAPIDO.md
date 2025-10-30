# 🚀 Guia Rápido de Uso

## Como Executar

```powershell
cd streamlit-etiquetas-correios
streamlit run app.py
```

**URL:** http://localhost:8502

---

## 📖 Passo a Passo

### 1️⃣ Upload de Arquivos
- Clique em **"Browse files"**
- Selecione um ou mais PDFs de NF-e
- **Dica:** Use Ctrl+Click para selecionar múltiplos arquivos

### 2️⃣ Processamento Automático
- Sistema processa automaticamente todos os PDFs
- Barra de progresso mostra o andamento
- Dados são extraídos e organizados

### 3️⃣ Revisão dos Dados
- Cada NF-e aparece em um painel expansível
- **Lado Esquerdo:** Dados do Remetente (Empresa) + NF
- **Lado Direito:** Dados do Destinatário
- **Edite** qualquer campo que estiver incorreto

### 4️⃣ Gerar Etiquetas
- Visualize o resumo: Total de etiquetas e páginas
- Clique em **"🎨 Gerar Etiquetas"**
- Aguarde processamento

### 5️⃣ Download
- Clique em **"⬇️ Download PDF"**
- Arquivo `etiquetas_correios.pdf` será baixado
- Pronto para impressão!

---

## 🎯 Campos Extraídos

### Remetente (Empresa)
- ✅ Nome da Empresa
- ✅ Endereço completo
- ✅ Cidade/Estado
- ✅ CEP

### Nota Fiscal
- ✅ Número da NF

### Destinatário
- ✅ Nome completo
- ✅ Endereço
- ✅ Bairro
- ✅ Cidade/Estado
- ✅ CEP

### Logística
- ✅ Volume (ex: 1/1, 1/3)
- ✅ Transportadora

---

## 📐 Layout do PDF

- **6 etiquetas por página** (2 colunas x 3 linhas)
- **Tamanho:** A4 (210 x 297 mm)
- **Bordas:** Pretas de 0.5mm para facilitar corte
- **Otimização:** Múltiplos PDFs combinados na mesma folha

### Exemplos

**Exemplo 1:** 4 NF-e
- Resultado: 1 página com 4 etiquetas

**Exemplo 2:** 9 NF-e
- Resultado: 2 páginas (6 + 3 etiquetas)

**Exemplo 3:** 15 NF-e
- Resultado: 3 páginas (6 + 6 + 3 etiquetas)

---

## 💡 Dicas

### Seleção Múltipla
- **Windows:** Ctrl + Click
- **Mac:** Cmd + Click

### Re-processar PDFs
- Clique em **"🔄 Re-processar PDFs"** se fez upload de novos arquivos

### Campos Vazios
- Se algum campo não for detectado, preencha manualmente
- Sistema aceita edições antes de gerar o PDF

### Impressão
- Configure impressora para **A4**
- Use **100% de escala** (sem ajuste automático)
- Modo **Retrato/Portrait**

---

## ⚠️ Troubleshooting

### PDF não processa?
- Verifique se é uma NF-e válida (DANFE)
- Certifique-se que o PDF tem texto (não é só imagem)

### Campos incorretos?
- Use os campos de edição para corrigir
- Layouts de DANFE variam entre emissores

### Erro ao gerar?
- Verifique se todos os campos obrigatórios estão preenchidos
- Recarregue a página e tente novamente

---

## 🎨 Interface

### Sidebar (Esquerda)
- 📋 Instruções
- 💡 Dicas
- ℹ️ Informações do sistema

### Área Principal
1. **Upload**: Arrastar ou clicar para upload
2. **Preview**: Dados extraídos organizados por arquivo
3. **Edição**: Formulários para cada campo
4. **Geração**: Botão principal e estatísticas
5. **Download**: Link para baixar PDF

---

## 🔥 Features Especiais

- ✅ **Processamento em Lote**: Múltiplos PDFs de uma vez
- ✅ **Otimização Inteligente**: Combina etiquetas para economizar papel
- ✅ **Edição em Tempo Real**: Correções instantâneas
- ✅ **Validação Visual**: Ícones e mensagens claras
- ✅ **Download Imediato**: Sem precisar salvar localmente

---

**Desenvolvido para máxima produtividade no envio pelos Correios** 📦✨
