# Teste manual no Windows 10 ou 11

Beta sem assinatura. Faz isto num PC real, com a tua conta normal. Não uses uma máquina de CI como prova final.

Antes de começar: guarda as notas e fecha o Notryn se já estiver aberto.

## Instalar

1. Abre o PowerShell.
2. Corre `irm https://notryn.com/install.ps1 | iex`.
3. Se o SmartScreen disser que o Windows protegeu o PC, escolhe **Mais informações** e depois **Executar mesmo assim**.
4. Se o Defender avisar, lê o aviso. Não desligues o Defender para acabar a instalação.
5. Confirma que a app ficou em `%LOCALAPPDATA%\Notryn\app`.

## Atalho

1. Abre o Menu Iniciar.
2. Procura **Notryn**.
3. O atalho deve abrir a janela, não uma pasta.

## Janela

1. A janela do Notryn abre.
2. Não fica um ecrã de erro.
3. Fechar a janela termina a app.

## Nota

1. Cria um Brain numa pasta tua, por exemplo `Documentos\Notas de teste`.
2. Cria uma nota com uma frase simples.
3. Fecha o Notryn e abre outra vez.
4. A nota continua lá, no ficheiro `.md` dessa pasta.

## Sync

1. Em definições, liga o GitHub Sync com um repositório privado teu.
2. Escreve uma linha, faz Sync now, e confirma no GitHub que o ficheiro mudou.
3. Não cole o token em lado nenhum fora da app.

## Actualizar

1. Guarda e fecha a janela.
2. Corre `& "$env:LOCALAPPDATA\Notryn\notryn.cmd" update`.
3. A versão nova abre. A nota de teste continua igual.
4. A pasta da versão anterior ficou em `%LOCALAPPDATA%\Notryn\.notryn-backups`.

## Rollback

1. Fecha a janela.
2. Corre `& "$env:LOCALAPPDATA\Notryn\notryn.cmd" rollback`.
3. A app volta à versão anterior.
4. A nota de teste continua igual.
5. Um segundo rollback pode voltar à versão mais nova.

## Desinstalar

1. Fecha a janela.
2. Corre `& "$env:LOCALAPPDATA\Notryn\notryn.cmd" uninstall`.
3. O atalho e a pasta `app` desaparecem.
4. A nota na tua pasta e os ficheiros em `%LOCALAPPDATA%\Notryn` (menos a app) ficam.

## SmartScreen e Defender

Anota o que o PC mostrou:

- SmartScreen apareceu? A frase exacta?
- **Mais informações** e **Executar mesmo assim** chegaram para abrir?
- O Defender bloqueou, pôs em quarentena, ou só avisou?
- O nome do ficheiro que ele apontou (`Notryn.exe` ou `notryn.exe`)?

Isto é um beta sem certificado. Um aviso aqui é esperado. Um bloqueio que não deixa instalar é um problema a reportar, com a frase do Windows, sem capturas que mostrem notas ou tokens.
