package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"bionicpro/cmd"
	"bionicpro/internal/httpserver"
	"bionicpro/internal/reporter"
)

func main() {
	ctx := context.Background()
	servConfig := cmd.Execute()

	rep := reporter.NewReporter(servConfig.Reporter)
	defer rep.Close()

	cCtx, cancel := context.WithCancel(ctx)
	httpServer := httpserver.New(&servConfig.Server, rep)
	go func() {
		if err := httpServer.Start(cCtx); err != nil {
			log.Fatalf("http server start failed: %v", err)
		}
	}()

	ch := make(chan os.Signal, 1)
	signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
	<-ch
	cancel()
}
