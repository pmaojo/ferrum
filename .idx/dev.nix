{ pkgs, ... }: {
  channel = "stable-24.05";

  packages = [
    pkgs.docker
    pkgs.docker-compose
    pkgs.docker-client
    pkgs.python311Packages.pip
    pkgs.nodejs_20
  ];

  env = {};

  idx = {
    extensions = [
      # Puedes añadir aquí VSCode extensions si usas IDX
    ];

    previews = {
      enable = true;
      previews = {
        web = {
          # Aquí asumimos que tu servicio se expone en el puerto 3000 del contenedor.
          command = ["docker-compose" "up"];
          manager = "web";
          env = {
            # IMPORTANTE: este $PORT lo asigna IDX dinámicamente
            PORT = "$PORT";
          };
        };
      };
    };

    workspace = {
      onCreate = {
        # Inicia Docker si no se encuentra corriendo y espera a que esté listo
        enable-docker = ''
          if ! pgrep dockerd >/dev/null; then
            sudo dockerd > /tmp/docker.log 2>&1 &
            for i in {1..30}; do
              if docker info >/dev/null 2>&1; then
                break
              fi
              sleep 1
            done
          fi
        '';
      };
      onStart = {
        # Reinicia Docker al volver a abrir el entorno si es necesario
        start-docker = ''
          if ! pgrep dockerd >/dev/null; then
            sudo dockerd > /tmp/docker.log 2>&1 &
            for i in {1..30}; do
              if docker info >/dev/null 2>&1; then
                break
              fi
              sleep 1
            done
          fi
        '';
      };
    };
  };
}
