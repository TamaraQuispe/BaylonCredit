#!/usr/bin/env node
// Activa el hook versionado .githooks/pre-commit al instalar dependencias.
// Se ejecuta como `postinstall`; no debe romper instalaciones fuera de un
// checkout de Git (Docker, tarballs, CI sin .git).
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";

const HOOKS_PATH = ".githooks";

function git(args, options = {}) {
  const output = execFileSync("git", args, {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });
  // Con stdio: "inherit" la salida no se captura y execFileSync devuelve null.
  return output ? String(output).trim() : "";
}

function main() {
  if (!existsSync(`${HOOKS_PATH}/pre-commit`)) {
    return 0; // El hook no forma parte de esta instalación (p. ej. imagen Docker).
  }

  try {
    if (git(["rev-parse", "--is-inside-work-tree"]) !== "true") {
      return 0;
    }
  } catch {
    return 0; // Git no disponible o directorio fuera de un repositorio.
  }

  let current = "";
  try {
    current = git(["config", "--local", "--get", "core.hooksPath"]);
  } catch {
    current = ""; // Sin configurar.
  }

  if (current === HOOKS_PATH) {
    console.log(`Hook de pre-commit ya activo (core.hooksPath=${HOOKS_PATH}).`);
    return 0;
  }

  if (current) {
    console.warn(
      `Aviso: core.hooksPath ya apunta a "${current}"; no se sobrescribe.`,
    );
    console.warn(
      `Para usar el hook del repo: git config core.hooksPath ${HOOKS_PATH}`,
    );
    return 0;
  }

  git(["config", "--local", "core.hooksPath", HOOKS_PATH], {
    stdio: "inherit",
  });
  console.log(`Hook de pre-commit activado (core.hooksPath=${HOOKS_PATH}).`);
  return 0;
}

process.exitCode = main();
