package main

import (
	"context"
	"log"
	"net"
	"os"

	"github.com/camunda/zeebe/clients/go/v8/pkg/pb"
	"google.golang.org/grpc"
)

type server struct {
	pb.UnimplementedGatewayServer
}

func (s *server) Topology(ctx context.Context, req *pb.TopologyRequest) (*pb.TopologyResponse, error) {
	return &pb.TopologyResponse{GatewayVersion: "mock"}, nil
}

func main() {
	addr := ":26500"
	if v := os.Getenv("LISTEN_ADDR"); v != "" {
		addr = v
	}
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer()
	pb.RegisterGatewayServer(s, &server{})
	log.Printf("zeebe gRPC mock listening on %s", addr)
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
