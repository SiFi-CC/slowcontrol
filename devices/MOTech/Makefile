CXX = g++
OS_NAME:=$(shell uname -s | tr A-Z a-z)
ifeq ($(OS_NAME),darwin)
STDINCDIR := -I/opt/local/include
STDLIBDIR := -L/opt/local/lib
else
STDINCDIR := 
STDLIBDIR := 
endif
CPPFLAGS := $(shell mysql_config --cxxflags) $(STDINCDIR)
LDFLAGS := $(shell mysql_config --libs) $(STDLIBDIR)
CPPFLAGS += -g
TARGET = MOTech
SRC = MOTech.cpp
OBJ = $(SRC:.cpp=.o)
all : $(TARGET)
$(TARGET) : $(OBJ)
	$(CXX) $(CPPFLAGS) -o $(TARGET) $(OBJ) $(LDFLAGS)
%.o : %.cpp
	$(CXX) $(CPPFLAGS) -o $@ -c $<
