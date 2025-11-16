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
        # Opcional: asegúrate que Docker esté activo
        enable-docker = "sudo dockerd > /tmp/docker.log 2>&1 &";
      };
      onStart = {
        # También podemos arrancar Docker al reiniciar el entorno
        start-docker = "sudo dockerd > /tmp/docker.log 2>&1 &";
      };
    };
  };
}
